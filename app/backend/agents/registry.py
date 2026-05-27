"""
Static registry of approved agent templates for agentic workflows.
"""
from typing import Dict, Type, Callable
from app.backend.agents.workers.scribe_decision_extractor import ScribeDecisionExtractor
from app.backend.agents.workers.scribe_assumption_extractor import ScribeAssumptionExtractor
from app.backend.agents.workers.scribe_issue_extractor import ScribeIssueExtractor
from app.backend.agents.workers.scribe_concept_summary_writer import ScribeConceptSummaryWriter
from app.backend.agents.workers.scribe_artifact_generator import ScribeArtifactGenerator

# Define the agent registry mapping task types to agent classes
AGENT_REGISTRY: Dict[str, Type] = {
    "scribe_decision_extractor": ScribeDecisionExtractor,
    "scribe_assumption_extractor": ScribeAssumptionExtractor,
    "scribe_issue_extractor": ScribeIssueExtractor,
    "scribe_concept_summary_writer": ScribeConceptSummaryWriter,
    "scribe_artifact_generator": ScribeArtifactGenerator,
}

# Alternative approach using callable functions (for simpler implementation)
AGENT_REGISTRY_FUNCTIONS: Dict[str, Callable] = {
    "scribe_decision_extractor": lambda: ScribeDecisionExtractor(),
    "scribe_assumption_extractor": lambda: ScribeAssumptionExtractor(),
    "scribe_issue_extractor": lambda: ScribeIssueExtractor(),
    "scribe_concept_summary_writer": lambda: ScribeConceptSummaryWriter(),
    "scribe_artifact_generator": lambda: ScribeArtifactGenerator(),
}
