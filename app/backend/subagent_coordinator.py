"""
Subagent Coordinator for managing specialized artifact generation agents.
This system enables the IKMAS system to spawn and coordinate subagents
for generating knowledge artifacts like definitions, concepts, quizzes, etc.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid
from app.infrastructure.tracing import traceable


class ArtifactType(str, Enum):
    """Types of knowledge artifacts that can be generated."""
    DEFINITION = "definition"
    CONCEPT = "concept"
    PREREQUISITE = "prerequisite"
    PITFALL = "pitfall"
    CASE = "case"
    QUIZ_ITEM = "quiz_item"


@dataclass
class ArtifactGenerationRequest:
    """Request for generating a specific type of artifact."""
    artifact_type: ArtifactType
    context: str  # Context or content to work with
    user_input: str  # Original user request
    session_id: str  # Session identifier for tracking
    related_artifacts: List[Dict[str, Any]] = None  # Previously generated artifacts
    target_audience: str = "general"  # Audience level (novice, intermediate, expert)


@dataclass
class ArtifactResult:
    """Result from artifact generation."""
    artifact_type: ArtifactType
    content: str
    metadata: Dict[str, Any]
    confidence: float = 0.0
    generated_at: str = None  # Timestamp
    source_artifacts: List[str] = None  # References to source artifacts


class SubagentCoordinator:
    """Coordinates the spawning and execution of specialized artifact generation agents."""
    
    def __init__(self):
        self.active_subagents: Dict[str, Any] = {}
        self.artifact_storage: Dict[str, ArtifactResult] = {}
        # Import agents here to avoid circular imports
        from app.backend.artifact_generators.definition_generator import DefinitionGeneratorAgent
        from app.backend.artifact_generators.concept_generator import ConceptMapperAgent
        from app.backend.artifact_generators.quiz_generator import QuizGeneratorAgent
        
        self.agent_factories = {
            ArtifactType.DEFINITION.value: DefinitionGeneratorAgent,
            ArtifactType.CONCEPT.value: ConceptMapperAgent,
            ArtifactType.QUIZ_ITEM.value: QuizGeneratorAgent,
        }
    
    @traceable(name="subagent_coordinator_spawn", run_type="chain")
    def spawn_subagent(self, agent_type: str, request: ArtifactGenerationRequest) -> str:
        """Spawn a new subagent for artifact generation."""
        subagent_id = f"subagent_{uuid.uuid4().hex[:8]}"
        
        # Store the subagent reference
        self.active_subagents[subagent_id] = {
            "type": agent_type,
            "request": request,
            "status": "pending"
        }
        
        return subagent_id
    
    @traceable(name="subagent_coordinator_execute", run_type="chain")  
    def execute_subagent(self, subagent_id: str, backend) -> ArtifactResult:
        """Execute a spawned subagent and return results."""
        if subagent_id not in self.active_subagents:
            raise ValueError(f"Subagent {subagent_id} not found")
        
        subagent_info = self.active_subagents[subagent_id]
        agent_type = subagent_info["type"]
        request = subagent_info["request"]
        
        # Execute the appropriate agent based on type
        result = self._execute_specific_agent(agent_type, request, backend)
        
        # Mark as completed
        self.active_subagents[subagent_id]["status"] = "completed"
        
        # Store artifact
        self.artifact_storage[result.artifact_type.value] = result
        
        return result
    
    def _execute_specific_agent(self, agent_type: str, request: ArtifactGenerationRequest, backend) -> ArtifactResult:
        """Execute specific agent type based on the agent factory mapping."""
        if agent_type not in self.agent_factories:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        
        # Create the agent instance
        agent_class = self.agent_factories[agent_type]
        agent = agent_class()
        
        # Create context for the agent
        from app.backend.artifact_generators.base_artifact_generator import ArtifactGenerationContext
        context = ArtifactGenerationContext(
            user_input=request.user_input,
            context_content=request.context,
            related_artifacts=request.related_artifacts or [],
            target_audience=request.target_audience,
            session_id=request.session_id
        )
        
        # Execute the agent
        result = agent.generate(context, backend)
        
        return result
    
    def generate_artifacts_sequentially(self, requests: List[ArtifactGenerationRequest], backend) -> List[ArtifactResult]:
        """Generate multiple artifacts sequentially."""
        results = []
        
        for request in requests:
            # Spawn subagent for this request
            subagent_id = self.spawn_subagent(request.artifact_type.value, request)
            
            # Execute the subagent
            result = self.execute_subagent(subagent_id, backend)
            results.append(result)
        
        return results
    
    def get_all_artifacts(self) -> Dict[str, ArtifactResult]:
        """Retrieve all generated artifacts."""
        return self.artifact_storage.copy()


# Global coordinator instance
subagent_coordinator = SubagentCoordinator()