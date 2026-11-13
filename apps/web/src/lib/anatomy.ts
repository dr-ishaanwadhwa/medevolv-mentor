export type SystemId =
  | 'skeletal'
  | 'muscular'
  | 'cardiac'
  | 'sensory'
  | 'arterial'
  | 'venous'
  | 'nervous'
  | 'respiratory'
  | 'digestive'
  | 'urinary'
  | 'lymphatic'
  | 'endocrine'
  | 'reproductive'
  | 'integumentary'
  | 'connective';

export interface SystemMeta {
  id: SystemId;
  name: string;
  color: string;
  description: string;
}

export const SYSTEMS: SystemMeta[] = [
  { id: 'skeletal', name: 'Skeleton', color: '#e2d9ba', description: 'Bones form the supporting framework of the body, protect organs, and provide attachment points for muscles.' },
  { id: 'muscular', name: 'Muscles', color: '#a85b50', description: 'Skeletal muscles generate movement by pulling on their attachments. Together with tendons, they move joints and stabilize posture.' },
  { id: 'cardiac', name: 'Heart', color: '#b96760', description: 'The heart is a muscular pump with four chambers. Its valves direct blood forward through pulmonary and systemic circuits.' },
  { id: 'sensory', name: 'Sensory organs', color: '#b0c8ce', description: 'Structures contributing to special senses including sight, hearing, and balance.' },
  { id: 'arterial', name: 'Arteries', color: '#c05245', description: 'Arteries carry oxygenated and systemic blood away from the heart to peripheral tissues.' },
  { id: 'venous', name: 'Veins', color: '#527c9f', description: 'Veins return deoxygenated blood from tissues toward the heart and pulmonary circulation.' },
  { id: 'nervous', name: 'Nervous system', color: '#d8b565', description: 'Brain, spinal cord, and peripheral nerves coordinating motor, sensory, and autonomic functions.' },
  { id: 'respiratory', name: 'Respiratory', color: '#b98991', description: 'Airways and lungs conducting gas exchange between alveolar air and capillary blood.' },
  { id: 'digestive', name: 'Digestive', color: '#b8916b', description: 'Gastrointestinal tract and accessory organs breaking down nutrients and absorbing water.' },
  { id: 'urinary', name: 'Urinary', color: '#b47961', description: 'Kidneys filtering blood, regulating electrolyte balance, and excreting waste via bladder.' },
  { id: 'lymphatic', name: 'Lymphatic', color: '#879f7c', description: 'Vessels and lymphoid tissue returning interstitial fluid and providing immune surveillance.' },
  { id: 'endocrine', name: 'Endocrine', color: '#c5a09a', description: 'Glandular organs secreting hormones regulating metabolism, growth, and homeostasis.' },
  { id: 'reproductive', name: 'Reproductive', color: '#bda098', description: 'Reproductive structures contributing to gametogenesis and sexual hormone production.' },
  { id: 'integumentary', name: 'Body surface', color: '#ba9b7d', description: 'Skin providing an outer anatomical protective boundary and thermoregulation.' },
  { id: 'connective', name: 'Connective tissue', color: '#aec3bb', description: 'Cartilage, fascia, and ligaments stabilizing joints and transmitting structural tension.' },
];

export interface Part {
  id: string;
  name: string;
  conceptId: string;
  system: SystemId;
  chunk: number;
  positions: number;
  normals: number;
  indices: number;
  vertexCount: number;
  indexCount: number;
  bounds: [number[], number[]];
}

export interface Concept {
  id: string;
  name: string;
  elements: string[];
}

export interface ChunkMeta {
  url: string;
  bytes: number;
  gzip?: string;
  gzipBytes?: number;
}

export interface Atlas {
  version: string;
  sex?: 'male';
  source?: string;
  scope?: string;
  parts: Part[];
  concepts: Concept[];
  chunks: ChunkMeta[];
  triangles: number;
}

export type View = 'three-quarter' | 'front' | 'back' | 'side' | 'anterior' | 'posterior' | 'lateral_left' | 'lateral_right' | 'superior' | 'isometric' | 'thoracic_left_oblique';

export interface SceneState {
  inspectorOpen?: boolean;
  explode: number;
  visible: SystemId[];
  selected: string[];
  isolate: boolean;
  view: View;
  rotate: boolean;
  reset: number;
}

export const DEFAULT_VISIBLE: SystemId[] = [
  'cardiac',
  'sensory',
  'skeletal',
  'muscular',
  'arterial',
  'venous',
  'nervous',
  'respiratory',
  'digestive',
  'urinary',
  'lymphatic',
  'endocrine',
  'reproductive',
  'connective',
];

export interface MereologyNode {
  fmaId: string;
  name: string;
  relation: string;
}

export interface CertifiedCondition {
  conditionId: string;
  name: string;
  relation: string;
  guidelineBadges?: string[];
}

export interface CitationPointer {
  book: string;
  edition: string;
  chapter: string;
  page: string;
  pointer: string;
  verifiedFact: string;
}

export interface ResolvedSpatialConcept {
  identifier: string;
  fmaId: string;
  canonicalName: string;
  latinName?: string;
  system: SystemId;
  meshPartIds: string[];
  boundingBox?: [[number, number, number], [number, number, number]];
  centroid?: [number, number, number];
  mereology?: {
    parents: MereologyNode[];
    children: MereologyNode[];
  };
  certifiedConditions?: CertifiedCondition[];
  citations?: CitationPointer[];
  socraticQuestions?: string[];
}

export type SpatialAction =
  | {
      type: 'spatial_action';
      action: 'highlight';
      conceptIds: string[];
      isolate?: boolean;
    }
  | {
      type: 'spatial_action';
      action: 'set_camera';
      preset: View;
      targetFmaId?: string;
      durationMs?: number;
    }
  | {
      type: 'spatial_action';
      action: 'dissect';
      visibleSystems?: SystemId[];
      peelSystems?: SystemId[];
    }
  | {
      type: 'spatial_action';
      action: 'reset';
    };
