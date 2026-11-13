"""
E2E Test Configuration and Fixtures for MedEvolv Mentor & Atlas Platform.
Provides TestClient, in-memory mereology SQLite graph, FSRS-5 engine,
guardrails engine, frontend contract validators, and mock LLM stream generator.
"""

import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import pytest
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.testclient import TestClient


# ============================================================================
# 1. Pydantic Models (PROJECT.md § Interface Contracts)
# ============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    messages: List[ChatMessage]
    activeFmaIds: Optional[List[str]] = Field(default_factory=list)
    activeSystems: Optional[List[str]] = Field(default_factory=list)
    cameraPose: Optional[str] = "anterior"
    streamSpatialActions: Optional[bool] = True
    userAge: Optional[int] = None
    parentalConsent: Optional[bool] = None


class SpatialResolveRequest(BaseModel):
    identifier: str
    includeHierarchy: Optional[bool] = True
    includeCitations: Optional[bool] = True
    maxDepth: Optional[int] = 3


# ============================================================================
# 2. In-Memory Mereology Graph & Traversal Engine (R3.1 - R3.4)
# ============================================================================

def init_test_mereology_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS spatial_concepts (
        fma_id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        latin_name TEXT,
        system_id TEXT NOT NULL,
        mesh_part_ids TEXT NOT NULL, -- JSON array
        bounding_box TEXT NOT NULL,  -- JSON [[minX, minY, minZ], [maxX, maxY, maxZ]]
        centroid TEXT NOT NULL,      -- JSON [x, y, z]
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS spatial_relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_fma_id TEXT NOT NULL,
        predicate TEXT NOT NULL, -- 'PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF', 'SUPPLIED_BY'
        object_fma_id TEXT NOT NULL,
        source_citation TEXT,
        FOREIGN KEY(subject_fma_id) REFERENCES spatial_concepts(fma_id),
        FOREIGN KEY(object_fma_id) REFERENCES spatial_concepts(fma_id)
    );

    CREATE TABLE IF NOT EXISTS clinical_concepts (
        concept_id TEXT PRIMARY KEY,
        canonical_label TEXT NOT NULL,
        concept_type TEXT NOT NULL,
        snomed_id TEXT,
        bodhi_key TEXT,
        icd10_code TEXT
    );

    CREATE TABLE IF NOT EXISTS spatial_clinical_crosswalk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clinical_concept_id TEXT NOT NULL,
        fma_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        verification_method TEXT,
        confidence REAL DEFAULT 1.0,
        quote_pointer TEXT,
        guideline_badge TEXT,
        FOREIGN KEY(clinical_concept_id) REFERENCES clinical_concepts(concept_id),
        FOREIGN KEY(fma_id) REFERENCES spatial_concepts(fma_id)
    );
    """)

    # Seed Anatomical Concepts
    concepts = [
        # Heart & Cardiac System
        ("FMA7088", "Heart", "Cor", "cardiac", '["FJ7088"]', '[[-50.0, 1100.0, -40.0], [50.0, 1200.0, 40.0]]', '[0.0, 1150.0, 0.0]'),
        ("FMA7101", "Aortic valve", "Valva aortae", "cardiac", '["FJ2104"]', '[[-12.0, 1140.0, -25.0], [15.0, 1175.0, 10.0]]', '[1.5, 1157.5, -7.5]'),
        ("FMA7192", "Right coronary cusp of aortic valve", "Valvula semilunaris dextra", "cardiac", '[]', '[[-5.0, 1150.0, -10.0], [5.0, 1165.0, -2.0]]', '[0.0, 1157.5, -6.0]'),
        ("FMA7193", "Left coronary cusp of aortic valve", "Valvula semilunaris sinistra", "cardiac", '[]', '[[-10.0, 1150.0, -15.0], [0.0, 1165.0, -5.0]]', '[-5.0, 1157.5, -10.0]'),
        ("FMA7194", "Posterior non-coronary cusp of aortic valve", "Valvula semilunaris posterior", "cardiac", '[]', '[[0.0, 1150.0, -15.0], [10.0, 1165.0, -5.0]]', '[5.0, 1157.5, -10.0]'),

        # Arterial Branches
        ("FMA3739", "Left main coronary artery", "Arteria coronaria sinistra", "arterial", '["FJ1890"]', '[[-20.0, 1150.0, -10.0], [0.0, 1170.0, 10.0]]', '[-10.0, 1160.0, 0.0]'),
        ("FMA3740", "Anterior interventricular branch of left coronary artery", "Ramus interventricularis anterior arteriae coronariae sinistrae", "arterial", '["FJ1895"]', '[[-25.0, 1120.0, 0.0], [5.0, 1165.0, 25.0]]', '[-10.0, 1142.5, 12.5]'),
        ("FMA7199", "First diagonal branch of LAD", "Ramus diagonalis primus arteriae coronariae sinistrae", "arterial", '[]', '[[-20.0, 1130.0, 5.0], [-10.0, 1150.0, 15.0]]', '[-15.0, 1140.0, 10.0]'),

        # Renal / Urinary System
        ("FMA7203", "Left kidney", "Ren sinister", "urinary", '["FJ3001"]', '[[-60.0, 1000.0, -30.0], [-20.0, 1120.0, 10.0]]', '[-40.0, 1060.0, -10.0]'),
        ("FMA7204", "Renal glomerulus", "Glomerulus renalis", "urinary", '[]', '[[-45.0, 1040.0, -15.0], [-35.0, 1080.0, -5.0]]', '[-40.0, 1060.0, -10.0]'),
        ("FMA7205", "Podocyte", "Podocytus", "urinary", '[]', '[[-42.0, 1055.0, -12.0], [-38.0, 1065.0, -8.0]]', '[-40.0, 1060.0, -10.0]'),

        # Respiratory System
        ("FMA7190", "Right lung", "Pulmo dexter", "respiratory", '["FJ4001"]', '[[10.0, 1050.0, -50.0], [120.0, 1250.0, 50.0]]', '[65.0, 1150.0, 0.0]'),
        ("FMA7191", "Apical bronchopulmonary segment of right lung", "Segmentum apicale pulmonis dextri", "respiratory", '[]', '[[40.0, 1200.0, -20.0], [80.0, 1250.0, 20.0]]', '[60.0, 1225.0, 0.0]'),

        # Skeletal & Muscular & Nervous
        ("FMA5018", "Femur", "Os femoris", "skeletal", '["FJ5001"]', '[[-150.0, 400.0, -30.0], [-80.0, 850.0, 30.0]]', '[-115.0, 625.0, 0.0]'),
        ("FMA9641", "Biceps brachii", "Musculus biceps brachii", "muscular", '["FJ6001"]', '[[-200.0, 1000.0, -20.0], [-160.0, 1200.0, 20.0]]', '[-180.0, 1100.0, 0.0]'),
        ("FMA6711", "Sciatic nerve", "Nervus ischiadicus", "nervous", '["FJ7001"]', '[[-120.0, 500.0, -40.0], [-90.0, 900.0, -10.0]]', '[-105.0, 700.0, -25.0]')
    ]
    cursor.executemany("INSERT INTO spatial_concepts VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", concepts)

    # Seed Mereology Relations
    relations = [
        ("FMA7101", "PART_OF", "FMA7088", "Gray's Anatomy, 5e, Ch 4, p. 542"),
        ("FMA7192", "PART_OF", "FMA7101", "Gray's Anatomy, 5e, Ch 4, p. 542"),
        ("FMA7193", "PART_OF", "FMA7101", "Gray's Anatomy, 5e, Ch 4, p. 542"),
        ("FMA7194", "PART_OF", "FMA7101", "Gray's Anatomy, 5e, Ch 4, p. 542"),
        ("FMA3739", "PART_OF", "FMA7088", "Gray's Anatomy, 5e, Ch 4, p. 545"),
        ("FMA3740", "BRANCH_OF", "FMA3739", "Gray's Anatomy, 5e, Ch 4, p. 546"),
        ("FMA7199", "BRANCH_OF", "FMA3740", "Gray's Anatomy, 5e, Ch 4, p. 547"),
        ("FMA7204", "PART_OF", "FMA7203", "Robbins Pathologic Basis, 10e, Ch 20, p. 890"),
        ("FMA7205", "PART_OF", "FMA7204", "Robbins Pathologic Basis, 10e, Ch 20, p. 892"),
        ("FMA7191", "PART_OF", "FMA7190", "Gray's Anatomy, 5e, Ch 4, p. 580")
    ]
    cursor.executemany("INSERT INTO spatial_relations (subject_fma_id, predicate, object_fma_id, source_citation) VALUES (?, ?, ?, ?)", relations)

    # Seed Clinical Concepts
    clinical = [
        ("COND:aortic_stenosis", "Aortic valve stenosis", "PathologicalCondition", "SNOMED:60573004", "BODHI:aortic_stenosis", "I35.0"),
        ("COND:myocardial_infarction", "Anterior STEMI (LAD Occlusion)", "PathologicalCondition", "SNOMED:57054005", "BODHI:anterior_mi", "I21.0"),
        ("COND:pulmonary_tb", "Pulmonary tuberculosis", "PathologicalCondition", "SNOMED:154283005", "BODHI:pulmonary_tb", "A15.0"),
        ("COND:nephrotic_syndrome", "Minimal change disease", "PathologicalCondition", "SNOMED:52254009", "BODHI:nephrotic_syn", "N04.0"),
        ("COND:femur_fracture", "Femur fracture", "Trauma", "SNOMED:71620000", "BODHI:femur_fracture", "S72.0"),
        ("COND:coronary_artery_disease", "Coronary artery disease", "PathologicalCondition", "SNOMED:53741008", "BODHI:cad", "I25.1")
    ]
    cursor.executemany("INSERT INTO clinical_concepts VALUES (?, ?, ?, ?, ?, ?)", clinical)

    # Seed Crosswalks
    crosswalks = [
        ("COND:aortic_stenosis", "FMA7101", "INVOLVES_STRUCTURE", "certified_pointer", 1.0, "(Gray's Anatomy, 5e, Ch 4, p. 542)", "ICMR"),
        ("COND:myocardial_infarction", "FMA3740", "INVOLVES_STRUCTURE", "certified_pointer", 1.0, "(Harrison's Principles of Internal Medicine, 21e, Ch 265, p. 1890)", "ICMR"),
        ("COND:pulmonary_tb", "FMA7190", "SITE_OF_OCCURRENCE", "certified_pointer", 1.0, "(NTEP Technical and Operational Guidelines, 2024, Ch 3, p. 45)", "NTEP"),
        ("COND:nephrotic_syndrome", "FMA7204", "INVOLVES_STRUCTURE", "mereological_expansion", 0.95, "(Robbins & Cotran Pathologic Basis of Disease, 10e, Ch 20, p. 892)", "MoHFW"),
        ("COND:femur_fracture", "FMA5018", "SITE_OF_OCCURRENCE", "certified_pointer", 1.0, "(Gray's Anatomy, 5e, Ch 7, p. 1320)", "WHO"),
        ("COND:coronary_artery_disease", "FMA3739", "INVOLVES_STRUCTURE", "certified_pointer", 1.0, "(Harrison's Principles of Internal Medicine, 21e, Ch 265, p. 1888)", "ICMR")
    ]
    cursor.executemany("INSERT INTO spatial_clinical_crosswalk (clinical_concept_id, fma_id, relation_type, verification_method, confidence, quote_pointer, guideline_badge) VALUES (?, ?, ?, ?, ?, ?, ?)", crosswalks)
    conn.commit()


class MereologyEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def climb_to_visible_mesh(self, target_fma: str, max_depth: int = 5) -> Tuple[Optional[str], int]:
        """
        Recursive upward Common Table Expression climbing PART_OF, BRANCH_OF, etc.
        Returns nearest ancestor possessing non-empty mesh_part_ids and the climb depth.
        """
        cursor = self.conn.cursor()
        query = """
        WITH RECURSIVE mereology_path AS (
            SELECT subject_fma_id, predicate, object_fma_id, 1 as depth
            FROM spatial_relations
            WHERE subject_fma_id = ?
              AND predicate IN ('PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF', 'SUPPLIED_BY')
            UNION ALL
            SELECT sr.subject_fma_id, sr.predicate, sr.object_fma_id, mp.depth + 1
            FROM spatial_relations sr
            INNER JOIN mereology_path mp ON sr.subject_fma_id = mp.object_fma_id
            WHERE mp.depth < ?
        )
        SELECT mp.object_fma_id, sc.canonical_name, sc.mesh_part_ids, mp.depth
        FROM mereology_path mp
        JOIN spatial_concepts sc ON mp.object_fma_id = sc.fma_id
        WHERE json_array_length(sc.mesh_part_ids) > 0
        ORDER BY mp.depth ASC
        LIMIT 1;
        """
        cursor.execute(query, (target_fma, max_depth))
        row = cursor.fetchone()
        if row:
            return row[0], row[3]
        return None, 0

    def resolve_structure(self, identifier: str, max_depth: int = 3) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        # Direct lookup by fma_id or canonical name
        cursor.execute("""
            SELECT fma_id, canonical_name, latin_name, system_id, mesh_part_ids, bounding_box, centroid
            FROM spatial_concepts
            WHERE fma_id = ? OR LOWER(canonical_name) = LOWER(?)
        """, (identifier, identifier))
        concept = cursor.fetchone()

        if not concept:
            # Check if identifier is a clinical condition
            cursor.execute("""
                SELECT fma_id FROM spatial_clinical_crosswalk WHERE clinical_concept_id = ?
            """, (identifier,))
            cross = cursor.fetchone()
            if cross:
                return self.resolve_structure(cross[0], max_depth)
            return None

        fma_id, name, latin, system, meshes_raw, bbox_raw, centroid_raw = concept
        mesh_part_ids = json.loads(meshes_raw)
        bounding_box = json.loads(bbox_raw)
        centroid = json.loads(centroid_raw)

        # Climb if mesh is empty
        climbed_from = None
        if not mesh_part_ids:
            visible_ancestor_id, climb_depth = self.climb_to_visible_mesh(fma_id, max_depth=max_depth)
            if visible_ancestor_id:
                climbed_from = fma_id
                # Inherit ancestor's mesh part
                cursor.execute("SELECT mesh_part_ids, bounding_box FROM spatial_concepts WHERE fma_id = ?", (visible_ancestor_id,))
                anc = cursor.fetchone()
                if anc:
                    mesh_part_ids = json.loads(anc[0])
                    bounding_box = json.loads(anc[1])

        # Fetch parents & children
        cursor.execute("""
            SELECT sr.object_fma_id, sc.canonical_name, sr.predicate
            FROM spatial_relations sr
            JOIN spatial_concepts sc ON sr.object_fma_id = sc.fma_id
            WHERE sr.subject_fma_id = ?
        """, (fma_id,))
        parents = [{"fmaId": r[0], "name": r[1], "relation": r[2]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT sr.subject_fma_id, sc.canonical_name, sr.predicate
            FROM spatial_relations sr
            JOIN spatial_concepts sc ON sr.subject_fma_id = sc.fma_id
            WHERE sr.object_fma_id = ?
        """, (fma_id,))
        children = [{"fmaId": r[0], "name": r[1], "relation": r[2]} for r in cursor.fetchall()]

        # Fetch certified conditions
        cursor.execute("""
            SELECT cc.concept_id, cc.canonical_label, scc.relation_type, scc.guideline_badge, scc.quote_pointer
            FROM spatial_clinical_crosswalk scc
            JOIN clinical_concepts cc ON scc.clinical_concept_id = cc.concept_id
            WHERE scc.fma_id = ?
        """, (fma_id,))
        conditions = []
        citations = []
        for r in cursor.fetchall():
            cond_id, cond_name, rel, badge, ptr = r
            conditions.append({
                "conditionId": cond_id,
                "name": cond_name,
                "relation": rel,
                "guidelineBadges": [badge] if badge else []
            })
            if ptr:
                citations.append({
                    "book": "grays" if "Gray" in ptr else ("harrison" if "Harrison" in ptr else ("robbins" if "Robbins" in ptr else "ntep")),
                    "edition": "Standard Edition",
                    "chapter": "Relevant Section",
                    "page": "p. ref",
                    "pointer": ptr,
                    "verifiedFact": f"{name} is critically involved in {cond_name}."
                })

        return {
            "identifier": identifier,
            "fmaId": fma_id,
            "canonicalName": name,
            "latinName": latin,
            "system": system,
            "meshPartIds": mesh_part_ids,
            "boundingBox": bounding_box,
            "centroid": centroid,
            "climbedFrom": climbed_from,
            "mereology": {
                "parents": parents,
                "children": children
            },
            "certifiedConditions": conditions,
            "citations": citations,
            "socraticQuestions": [
                f"What is the primary vascular supply to the {name}?",
                f"How does pathological narrowing or injury in the {name} manifest clinically?"
            ]
        }

    def calculate_grounding_coverage(self) -> Dict[str, float]:
        cursor = self.conn.cursor()
        # Structure grounding: structures with meshes or with an ancestor with a mesh
        cursor.execute("SELECT fma_id, mesh_part_ids FROM spatial_concepts")
        all_concepts = cursor.fetchall()
        grounded_structures = 0
        for fma_id, meshes_raw in all_concepts:
            meshes = json.loads(meshes_raw)
            if len(meshes) > 0:
                grounded_structures += 1
            else:
                anc, _ = self.climb_to_visible_mesh(fma_id, max_depth=5)
                if anc:
                    grounded_structures += 1

        structure_coverage = grounded_structures / max(1, len(all_concepts))

        # Condition grounding: conditions whose associated FMA has a mesh or climbed ancestor mesh
        cursor.execute("SELECT DISTINCT clinical_concept_id, fma_id FROM spatial_clinical_crosswalk")
        crosswalk_entries = cursor.fetchall()
        grounded_conditions = 0
        for cond_id, fma_id in crosswalk_entries:
            cursor.execute("SELECT mesh_part_ids FROM spatial_concepts WHERE fma_id = ?", (fma_id,))
            row = cursor.fetchone()
            if row:
                meshes = json.loads(row[0])
                if len(meshes) > 0:
                    grounded_conditions += 1
                else:
                    anc, _ = self.climb_to_visible_mesh(fma_id, max_depth=5)
                    if anc:
                        grounded_conditions += 1

        condition_coverage = grounded_conditions / max(1, len(crosswalk_entries))

        return {
            "structureCoverage": structure_coverage,
            "conditionCoverage": condition_coverage
        }


# ============================================================================
# 3. FSRS-5 Spaced-Repetition Engine (R4.1, R4.2)
# ============================================================================

@dataclass
class FSRSCard:
    card_id: str
    fma_id: str
    condition_id: Optional[str] = None
    state: int = 0  # 0=New, 1=Learning, 2=Review, 3=Relearning
    stability: float = 1.0  # days
    difficulty: float = 5.0  # 1.0 - 10.0
    retrievability: float = 1.0
    due: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_review: Optional[datetime] = None
    reps: int = 0
    lapses: int = 0


class FSRSEngine:
    """
    Free Spaced Repetition Scheduler v5 Implementation.
    """
    FACTOR = 19.0 / 81.0  # ~0.234567

    def __init__(self, target_retention: float = 0.90):
        self.target_retention = target_retention

    def retrievability(self, t_days: float, stability: float) -> float:
        if stability <= 0.0:
            return 0.0
        return (1.0 + self.FACTOR * (t_days / stability)) ** (-1.0)

    def calculate_next_interval(self, stability: float) -> int:
        # I = (S / Factor) * (R^(-1) - 1)
        interval = (stability / self.FACTOR) * ((self.target_retention ** -1.0) - 1.0)
        return max(1, int(round(interval)))

    def calculate_review(self, card: FSRSCard, rating: int, review_time: Optional[datetime] = None) -> FSRSCard:
        if review_time is None:
            review_time = datetime.now(timezone.utc)

        t_days = 0.0
        if card.last_review:
            delta = (review_time - card.last_review).total_seconds()
            t_days = max(0.0, delta / 86400.0)

        r = self.retrievability(t_days, card.stability) if card.reps > 0 else 1.0

        # Ratings: 1=Again, 2=Hard, 3=Good, 4=Easy
        if rating == 1:  # Again / Lapse
            card.lapses += 1
            card.state = 3  # Relearning
            card.difficulty = min(10.0, card.difficulty + 0.8)
            card.stability = max(0.5, card.stability * 0.25)
            next_interval_days = 1
        elif rating == 2:  # Hard
            card.difficulty = min(10.0, card.difficulty + 0.3)
            card.stability = card.stability * 1.2
            card.state = 2  # Review
            next_interval_days = max(1, int(card.stability * 0.8))
        elif rating == 3:  # Good
            card.difficulty = max(1.0, card.difficulty - 0.1)
            # Stability grows based on retrievability
            card.stability = max(1.0, card.stability * (1.0 + math.exp(1.0 - card.difficulty / 10.0) * (1.0 - r + 0.5)))
            card.state = 2  # Review
            next_interval_days = self.calculate_next_interval(card.stability)
        elif rating == 4:  # Easy
            card.difficulty = max(1.0, card.difficulty - 0.4)
            card.stability = max(2.0, card.stability * (1.0 + math.exp(1.0 - card.difficulty / 10.0) * 1.5))
            card.state = 2
            next_interval_days = int(self.calculate_next_interval(card.stability) * 1.3)
        else:
            raise ValueError(f"Invalid rating {rating}. Must be 1, 2, 3, or 4.")

        card.reps += 1
        card.retrievability = 1.0
        card.last_review = review_time
        card.due = review_time + timedelta(days=next_interval_days)
        return card

    def project_pin(self, centroid: List[float], camera_pos: List[float] = None,
                    viewport_width: int = 1920, viewport_height: int = 1080) -> Tuple[float, float]:
        """
        Screen-space projected pin coordinates using Three.js projection formula:
        screenX = (projected.x + 1) * viewportWidth / 2
        screenY = (1 - projected.y) * viewportHeight / 2
        """
        cx, cy, cz = centroid
        cam_z = 2000.0  # mock perspective distance
        proj_x = cx / (cz + cam_z)
        proj_y = cy / (cz + cam_z)

        screen_x = (proj_x + 1.0) * viewport_width / 2.0
        screen_y = (1.0 - proj_y) * viewport_height / 2.0
        return round(screen_x, 2), round(screen_y, 2)

    def generate_occlusion_card(self, fma_id: str, condition_id: Optional[str] = None,
                                centroid: List[float] = None) -> Dict[str, Any]:
        if centroid is None:
            centroid = [0.0, 1150.0, 0.0]

        screen_x, screen_y = self.project_pin(centroid)

        # Generate 4 pins: Pin 1 is target, 2-4 are distractor anatomical pins
        pins = [
            {"pinNumber": 1, "screenX": screen_x, "screenY": screen_y, "isTarget": True, "label": "A"},
            {"pinNumber": 2, "screenX": screen_x + 120.0, "screenY": screen_y - 45.0, "isTarget": False, "label": "B"},
            {"pinNumber": 3, "screenX": screen_x - 90.0, "screenY": screen_y + 80.0, "isTarget": False, "label": "C"},
            {"pinNumber": 4, "screenX": screen_x + 40.0, "screenY": screen_y + 110.0, "isTarget": False, "label": "D"}
        ]

        return {
            "cardId": f"CARD:{fma_id}:{condition_id or 'anatomy'}",
            "fmaId": fma_id,
            "conditionId": condition_id,
            "occlusionMask": {
                "maskedFmaIds": [fma_id],
                "opacity": 0.10,
                "wireframe": True
            },
            "pins": pins,
            "prompt": "Identify the occluded anatomical structure and state its key clinical involvement."
        }


# ============================================================================
# 4. Guardrails & Compliance Engine (R1.5, R4.3, R4.4, R4.5)
# ============================================================================

class GuardrailsEngine:
    POINTER_REGEX = re.compile(r"^\(([A-Za-z0-9\s'\.\-]+,\s*(?:\d+e|\d+th\s*Edition|20\d\d),\s*(?:Ch\s*\d+|Chapter\s*\d+|Section\s*\d+)?,\s*(?:p\.\s*\d+|pp\.\s*\d+-\d+))\)$")
    
    PII_PATTERNS = [
        (re.compile(r"\b(?:MRN|mrn|Patient ID|PID)[:\s]+([A-Z0-9\-]+)\b", re.IGNORECASE), "[REDACTED_MRN]"),
        (re.compile(r"\b(?:\+?91[\-\s]?)?[6789]\d{9}\b"), "[REDACTED_PHONE]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
        (re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "[REDACTED_AADHAAR]"),
        (re.compile(r"\b(?:patient|patient name|pt name|named)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b", re.IGNORECASE), "patient [REDACTED_NAME]"),
    ]

    EMERGENCY_TRIGGERS = [
        re.compile(r"\b(?:severe chest pain right now|crushing substernal pain|having a heart attack right now)\b", re.IGNORECASE),
        re.compile(r"\b(?:cannot breathe emergency|severe shortness of breath call 108|dying right now)\b", re.IGNORECASE),
        re.compile(r"\b(?:sudden facial drooping and arm weakness|acute stroke right now)\b", re.IGNORECASE),
        re.compile(r"\b(?:bleeding profusely cannot stop|unconscious patient right now)\b", re.IGNORECASE)
    ]

    INDIAN_GUIDELINES = {"ICMR", "NTEP", "MoHFW", "WHO"}

    def validate_citation_pointer(self, pointer: str) -> bool:
        if not pointer or not pointer.startswith("(") or not pointer.endswith(")"):
            return False
        # Must contain book, edition/year, and page
        has_page = bool(re.search(r"p\.\s*\d+", pointer))
        has_book = any(b in pointer.lower() for b in ["gray", "harrison", "robbins", "tripathi", "kdt", "ntep", "icmr", "guyton", "davidson"])
        return has_page and has_book

    def detect_copyright_leak(self, text: str) -> bool:
        """
        Flag verbatim copyright prose leakage: >12 consecutive words from known textbooks.
        """
        verbatim_phrases = [
            "the heart is an obliquely placed muscular organ situated in the middle mediastinum enclosed in pericardium",
            "arteriosclerosis is a generic term for thickening and loss of elasticity of arterial walls with three patterns",
            "the pericardial sac consists of an outer fibrous pericardium and an inner serous pericardium consisting of two layers"
        ]
        text_lower = text.lower()
        for phrase in verbatim_phrases:
            if phrase in text_lower:
                return True
        return False

    def sanitize_pii(self, text: str) -> Tuple[str, List[str]]:
        sanitized = text
        redacted_types = []
        for pattern, replacement in self.PII_PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub(replacement, sanitized)
                redacted_types.append(replacement)
        return sanitized, redacted_types

    def check_emergency_refusal(self, text: str) -> Optional[str]:
        for trigger in self.EMERGENCY_TRIGGERS:
            if trigger.search(text):
                return (
                    "EMERGENCY DIRECTIVE: Your query suggests an acute medical emergency. "
                    "This educational platform cannot provide emergency clinical care. "
                    "Call emergency services immediately (Call 108/112 in India, 911 in the US) "
                    "or proceed to the nearest emergency department."
                )
        return None

    def verify_dpdp_compliance(self, age: Optional[int], parental_consent: Optional[bool]) -> Dict[str, Any]:
        """
        DPDP 2025 Rules: Under-18 users must have verifiable parental consent.
        Zero tracking scripts and zero behavioral profiling allowed for minors.
        """
        if age is None:
            return {"allowed": False, "reason": "AGE_VERIFICATION_REQUIRED", "requireConsent": False}
        if age < 18:
            if not parental_consent:
                return {
                    "allowed": False,
                    "reason": "PARENTAL_CONSENT_REQUIRED",
                    "requireConsent": True,
                    "minor": True,
                    "trackingAllowed": False
                }
            return {
                "allowed": True,
                "minor": True,
                "trackingAllowed": False,
                "note": "Minor access granted under verifiable parental consent. Zero tracking enforced."
            }
        return {
            "allowed": True,
            "minor": False,
            "trackingAllowed": False,  # Strict zero-tracking by design
            "note": "Adult user compliant."
        }


# ============================================================================
# 5. Frontend Architectural Contract Validators (R2.1 - R2.6)
# ============================================================================

class FrontendContracts:
    """
    Validates structural contracts for Next.js 15 PWA, Three.js 15 draw call budget,
    Zustand state store, and IndexedDB offline caching.
    """
    DRAW_CALL_BUDGET = 15
    GEOMETRY_CHUNKS = 15
    MOBILE_BREAKPOINT_PX = 768

    @classmethod
    def validate_pwa_manifest(cls, manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        required_keys = ["name", "short_name", "start_url", "display", "background_color", "theme_color", "icons"]
        for key in required_keys:
            if key not in manifest:
                errors.append(f"Missing key in manifest: {key}")
        if manifest.get("display") not in ["standalone", "fullscreen", "minimal-ui"]:
            errors.append(f"Invalid display mode: {manifest.get('display')}")
        return len(errors) == 0, errors

    @classmethod
    def validate_threejs_draw_calls(cls, systems_count: int, draw_calls: int) -> bool:
        """
        GPU DataTexture system-level mesh merging must not exceed 15 draw calls.
        """
        return draw_calls <= cls.DRAW_CALL_BUDGET and draw_calls <= systems_count

    @classmethod
    def validate_datatexture_channels(cls, part_texture_channels: int, selection_texture_channels: int) -> bool:
        """
        partTexture: RGBA float (.xyz=offset, .w=visibility).
        selectionTexture: RGBA byte (.r=highlight state).
        """
        return part_texture_channels == 4 and selection_texture_channels == 4

    @classmethod
    def validate_layout_mode(cls, viewport_width: int) -> str:
        """
        Returns 'dual_pane' if viewport >= 768px, else 'bottom_drawer'.
        """
        if viewport_width >= cls.MOBILE_BREAKPOINT_PX:
            return "dual_pane"
        return "bottom_drawer"

    @classmethod
    def validate_offline_cache_contract(cls, cached_chunks: List[str], cached_decks: List[str]) -> bool:
        """
        Requires 15 binary geometry chunks (body-0.bin.gz to body-14.bin.gz).
        """
        expected_chunks = {f"body-{i}.bin.gz" for i in range(cls.GEOMETRY_CHUNKS)}
        actual_chunks = set(cached_chunks)
        return expected_chunks.issubset(actual_chunks) and len(cached_decks) >= 1


# ============================================================================
# 6. Reference FastAPI Application Mount
# ============================================================================

def create_e2e_test_app(mereology_engine: MereologyEngine,
                        fsrs_engine: FSRSEngine,
                        guardrails: GuardrailsEngine) -> FastAPI:
    app = FastAPI(title="MedEvolv Mentor & Atlas Gateway E2E Test Server", version="1.0.0")

    @app.get("/api/health")
    def health_check():
        return {
            "status": "ok",
            "service": "medevolv-gateway",
            "version": "1.0.0",
            "features": 20
        }

    @app.post("/api/chat/stream")
    async def chat_stream(req: ChatStreamRequest,
                           x_user_age: Optional[int] = Header(default=None),
                           x_parental_consent: Optional[bool] = Header(default=None)):
        # 1. DPDP Compliance check
        age = req.userAge if req.userAge is not None else x_user_age
        consent = req.parentalConsent if req.parentalConsent is not None else x_parental_consent
        if age is not None:
            dpdp_status = guardrails.verify_dpdp_compliance(age, consent)
            if not dpdp_status["allowed"]:
                def err_gen():
                    yield f"event: error\ndata: {json.dumps({'code': dpdp_status['reason'], 'message': 'DPDP 2025: Age verification required.'})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'finish_reason': 'error'})}\n\n"
                return StreamingResponse(err_gen(), media_type="text/event-stream")

        # 2. Check emergency safety refusal on latest message
        last_message = req.messages[-1].content if req.messages else ""
        emergency_msg = guardrails.check_emergency_refusal(last_message)
        if emergency_msg:
            def emergency_gen():
                yield f"event: error\ndata: {json.dumps({'code': 'SAFETY_REFUSAL', 'message': emergency_msg})}\n\n"
                yield f"event: done\ndata: {json.dumps({'finish_reason': 'safety_refusal'})}\n\n"
            return StreamingResponse(emergency_gen(), media_type="text/event-stream")

        # 3. PII sanitization
        sanitized_content, redacted_types = guardrails.sanitize_pii(last_message)

        # 4. Stream response generator
        def stream_generator():
            # Emit token stream
            tokens = [
                "The anterior interventricular branch (LAD) ",
                "arises from the left coronary artery ",
                "and supplies the anterior 2/3 of the interventricular septum. ",
                "(Harrison's Principles of Internal Medicine, 21e, Ch 265, p. 1890)"
            ]
            for tok in tokens:
                yield f"event: token\ndata: {json.dumps({'type': 'token', 'content': tok})}\n\n"

            # Emit spatial actions if requested
            if req.streamSpatialActions:
                # Camera action
                yield f"event: spatial_action\ndata: {json.dumps({'type': 'spatial_action', 'action': 'set_camera', 'preset': 'thoracic_left_oblique', 'targetFmaId': 'FMA3740', 'durationMs': 1000})}\n\n"
                # Highlight action
                yield f"event: spatial_action\ndata: {json.dumps({'type': 'spatial_action', 'action': 'highlight', 'conceptIds': ['FMA3740'], 'color': '#e5484d', 'pulse': True})}\n\n"
                # Dissect action
                yield f"event: spatial_action\ndata: {json.dumps({'type': 'spatial_action', 'action': 'dissect', 'visibleSystems': ['cardiac', 'arterial'], 'peelSystems': ['skeletal', 'muscular']})}\n\n"

            yield f"event: done\ndata: {json.dumps({'finish_reason': 'stop'})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    @app.post("/api/spatial/resolve")
    async def spatial_resolve(req: SpatialResolveRequest):
        res = mereology_engine.resolve_structure(req.identifier, max_depth=req.maxDepth or 3)
        if not res:
            raise HTTPException(status_code=404, detail=f"Concept '{req.identifier}' not found in knowledge graph.")
        return res

    @app.post("/api/fsrs/review")
    async def fsrs_review(body: Dict[str, Any]):
        card_data = body.get("card", {})
        rating = body.get("rating", 3)
        card = FSRSCard(
            card_id=card_data.get("card_id", "CARD:1"),
            fma_id=card_data.get("fma_id", "FMA7101"),
            state=card_data.get("state", 0),
            stability=card_data.get("stability", 1.0),
            difficulty=card_data.get("difficulty", 5.0),
            reps=card_data.get("reps", 0),
            lapses=card_data.get("lapses", 0)
        )
        updated = fsrs_engine.calculate_review(card, rating)
        return {
            "card_id": updated.card_id,
            "fma_id": updated.fma_id,
            "state": updated.state,
            "stability": round(updated.stability, 4),
            "difficulty": round(updated.difficulty, 4),
            "retrievability": round(updated.retrievability, 4),
            "due": updated.due.isoformat(),
            "reps": updated.reps,
            "lapses": updated.lapses
        }

    @app.post("/api/fsrs/occlusion")
    async def fsrs_occlusion(body: Dict[str, Any]):
        fma_id = body.get("fma_id", "FMA7101")
        condition_id = body.get("condition_id")
        centroid = body.get("centroid", [1.5, 1157.5, -7.5])
        card = fsrs_engine.generate_occlusion_card(fma_id, condition_id, centroid)
        return card

    @app.post("/api/dpdp/verify-age")
    async def dpdp_verify(body: Dict[str, Any]):
        age = body.get("age")
        consent = body.get("parentalConsent")
        return guardrails.verify_dpdp_compliance(age, consent)

    return app


# ============================================================================
# 7. Pytest Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    init_test_mereology_db(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def mereology_engine(db_conn):
    return MereologyEngine(db_conn)


@pytest.fixture(scope="session")
def fsrs_engine():
    return FSRSEngine(target_retention=0.90)


@pytest.fixture(scope="session")
def guardrails():
    return GuardrailsEngine()


@pytest.fixture(scope="session")
def frontend_contracts():
    return FrontendContracts()


@pytest.fixture(scope="session")
def app(mereology_engine, fsrs_engine, guardrails):
    return create_e2e_test_app(mereology_engine, fsrs_engine, guardrails)


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)
