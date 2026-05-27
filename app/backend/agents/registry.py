"""
Static registry of approved agent templates for agentic workflows.
"""
from typing import Dict, Type, Callable
from app.backend.agents.workers.scribe_decision_extractor import ScribeDecisionExtractor
from app.backend.agents.workers.scribe_assumption_extractor import ScribeAssumptionExtractor
from app.backend.agents.workers.scribe_issue_extractor import ScribeIssueExtractor

# Define the agent registry mapping task types to agent classes
AGENT_REGISTRY: Dict[str, Type] = {
    "scribe_decision_extractor": ScribeDecisionExtractor,
    "scribe_assumption_extractor": ScribeAssumptionExtractor,
    "scribe_issue_extractor": ScribeIssueExtractor,
}

# Alternative approach using callable functions (for simpler implementation)
AGENT_REGISTRY_FUNCTIONS: Dict[str, Callable] = {
    "scribe_decision_extractor": lambda: ScribeDecisionExtractor(),
    "scribe_assumption_extractor": lambda: ScribeAssumptionExtractor(),
    "scribe_issue_extractor": lambda: ScribeIssueExtractor(),
}