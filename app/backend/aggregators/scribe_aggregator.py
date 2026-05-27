"""
Scribe Aggregator for combining task results into a reusable knowledge artifact.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.backend.workflow.task_models import AgentTaskResult

class ScribeArtifact(BaseModel):
    """Reusable knowledge artifact produced by Scribe agent."""
    artifact_type: str = "reusable_knowledge_artifact"
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    open_issues: List[Dict[str, Any]] = Field(default_factory=list)
    learning_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    flashcards: List[Dict[str, Any]] = Field(default_factory=list)
    artefacts: List[Dict[str, Any]] = Field(default_factory=list)
    reuse_guidance: List[str] = Field(default_factory=list)
    source_map: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)

class ScribeAggregator:
    """Aggregates results from Scribe worker tasks into a knowledge artifact."""
    
    def aggregate(self, results: List[AgentTaskResult]) -> ScribeArtifact:
        """Aggregate task results into a structured knowledge artifact."""
        artifact = ScribeArtifact()
        
        # Process each task result
        for result in results:
            if result.status != "success" or not result.output:
                continue
                
            output = result.output
            
            # Handle decision extraction results
            if "decisions" in output:
                artifact.decisions.extend(output["decisions"])
                
            # Handle assumption extraction results
            if "assumptions" in output:
                artifact.assumptions.extend(output["assumptions"])
                
            # Handle open issue extraction results
            if "open_issues" in output:
                artifact.open_issues.extend(output["open_issues"])

            if "learning_summaries" in output:
                artifact.learning_summaries.extend(output["learning_summaries"])

            if "flashcards" in output:
                artifact.flashcards.extend(output["flashcards"])

            if "artefacts" in output:
                artifact.artefacts.extend(output["artefacts"])
            
            # Add source mapping info
            artifact.source_map.append({
                "task_id": result.task_id,
                "agent_role": result.agent_role,
                "section": output.get("section", "")
            })
        
        # Generate reuse guidance based on extracted information
        if artifact.decisions:
            artifact.reuse_guidance.append("This artifact contains key project decisions.")
        
        if artifact.assumptions:
            artifact.reuse_guidance.append("Review assumptions before reusing in different contexts.")
            
        if artifact.open_issues:
            artifact.reuse_guidance.append("Consider open issues when applying this knowledge.")

        if artifact.learning_summaries:
            artifact.reuse_guidance.append("Use the learning summaries as study sheets and validate them against lecture material.")

        if artifact.flashcards:
            artifact.reuse_guidance.append("Use the flashcards for active recall and spaced repetition.")

        if artifact.artefacts:
            artifact.reuse_guidance.append("Store and reuse the generated artefacts in the knowledge base.")
        
        # Add confidence notes
        if (
            not artifact.decisions
            and not artifact.assumptions
            and not artifact.open_issues
            and not artifact.learning_summaries
            and not artifact.flashcards
            and not artifact.artefacts
        ):
            artifact.confidence_notes.append("No structured information extracted.")
        else:
            artifact.confidence_notes.append("Artifact created from explicit signals in the provided input.")
            
        return artifact
