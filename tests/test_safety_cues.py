"""api/safety_cues.patient_scoped: patient-scoped questions get no diagram, videos or topic (PRD section 5)."""
import pytest

from api.safety_cues import patient_scoped

PATIENT = [
    "My mother has chest pain, what should I give her?",
    "my father is on warfarin and has a nosebleed",
    "Should I take aspirin with ibuprofen?",
    "can I stop my metformin?",
    "I have a persistent cough and night sweats",
    "I'm taking amlodipine 10 mg, is it safe with grapefruit?",
    "What dose of paracetamol should I give my 3 year old?",
    "how many mg of amoxicillin for my daughter",
    "My patient has a fever and a rash, what do I do?",
    "A patient with MI: what dose of heparin should I give?",
    "Is 500 mg of metronidazole safe for me?",
    "My wife is 8 weeks pregnant and has fever",
    "I think I have diabetes",
    "what should I do about this lump",
    "How much should she take?",              # the existing rag.answer PERSONAL regex still applies
]
STUDY = [
    "What is the mechanism of action of metformin?",
    "Classify nephrotic syndrome",
    "Explain the pathogenesis of rheumatic fever",
    "Why is alpha blockade started before beta blockade in pheochromocytoma?",
    "Draw the blood supply of the heart",
    "A 45-year-old man presents with crushing chest pain. What is the most likely diagnosis?",
    "Branches of the facial nerve",
    "Differences between Crohn's disease and ulcerative colitis",
    "What is the loading dose of digoxin",
]


@pytest.mark.parametrize("q", PATIENT)
def test_patient_cues_are_scoped(q):
    assert patient_scoped(q), q


@pytest.mark.parametrize("q", STUDY)
def test_plain_study_questions_are_not_scoped(q):
    assert not patient_scoped(q), q


@pytest.mark.parametrize("q", [None, "", "   "])
def test_empty_is_not_scoped(q):
    assert patient_scoped(q) is False
