# Architecture Decision Records

##ADR-001: Agentic Workflow Architecture

### Status
Accepted

### Context
IKMAS needed to evolve from a static role-routed assistant to a controlled agentic knowledge-work system while maintaining safety, observability, and testability.

### Decision
Implement a controlled agentic workflow architecture where:
1. Parent agents propose structured TaskPlans
2. WorkflowController validates and executes these plans
3. Approved agent templates handle subtasks
4. Aggregators synthesize final results
5. Execution traces are maintained for transparency

### Consequences
✅ Benefits:
- Controlled agent spawning (no recursion)
- Deterministic execution model
- Transparent execution traces
- Testable components
- Safe deployment

❌ Drawbacks:
- More complex initial implementation
- Need for explicit task contracts
- Limited to approved agent templates

## ADR-002: Typed Workflow Models

### Status
Accepted

### Context
Need for strong typing in workflow components to prevent errors and improve maintainability.

### Decision
Replace generic dict structures with Pydantic models for all workflow components:
- TaskPlan
- TaskSpec  
- AgentTaskResult
- AgentTrace
- ExecutionBudget
- WorkflowResult

### Consequences
✅ Benefits:
- Compile-time type checking
- Runtime validation
- Clear interfaces
- Better IDE support
- Easier testing

❌ Drawbacks:
- More verbose code initially
- Need for careful schema design