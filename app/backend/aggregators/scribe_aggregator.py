"""
Scribe Aggregator for combining task results into a reusable knowledge artifact.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.backend.workflow.task_models import AgentTaskResult

class ScribeArtifact(BaseModel):
    """Reusable knowledge artifact produced by Scribe agent."""
    artifact_type: str = "reusable_knowledge_artifact"
    decisions: List[Dict[str, Any]] = []
    assumptions: List[Dict[str, Any]] = []
    open_issues: List[Dict[str, Any]] = []
    reuse_guidance: List[str] = []
    source_map: List[Dict[str, Any]] = []
    confidence_notes: List[str] = []

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
        
        # Add confidence notes
        if not artifact.decisions and not artifact.assumptions and not artifact.open_issues:
            artifact.confidence_notes.append("No structured information extracted.")
        else:
            artifact.confidence_notes.append("Artifact created with high confidence based on structured extraction.")
            
        return artifact