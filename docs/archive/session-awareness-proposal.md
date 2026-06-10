# IKMAS Session-Aware Routing: Scope-Aligned Enhancement

**Based on:** GeNeMe 2026 Abstract (submitted May 2026)  
**Scope:** Enhances existing components, adds no new architecture  
**Effort estimate:** 2-3 days implementation + 1 evaluation question

---

## What's Already in Your Abstract

| Component | What's Described |
|-----------|-----------------|
| **(1) User Interaction Layer** | Workers submit requests + context |
| **(2) LLM-Based Router** | Classifies by SECI mode + reuse situation |
| **(3) Structured Knowledge Layer** | Artifact lookup + vector search |
| **(4) Specialized GenAI Agents** | 4 roles: Scribe, Semantic Linking, Mentor, Context Reconstructor |
| **(5) Finite State Machine** | Maps SECI × Markus, assigns states, handles transitions |
| **Evaluation** | Vignette-based scenarios, post-task assessment, qualitative feedback |

---

## The Problem Your Abstract Implies (But Doesn't Solve)

> "The router classifies requests according to knowledge conversion mode and knowledge reuse situation"

**Implied limitation:** Each request is classified *in isolation*. The router has no memory of:
- Previous similar requests from the same user
- Knowledge gaps identified in past sessions
- Artefacts the system already knows exist
- Recurring themes that never got externalized

This means the FSM makes the same "first-time" decision every time, even for recurring problems.

---

## Minimal Enhancement: Session-Aware Routing

### Core Idea
Give the router **read access to session history** so classifications improve over time, without changing the architecture.

### Changes by Component

#### Component 2: Router Enhancement (~50 lines)

Before classification, the router queries session history:

```python
# PSEUDOCODE — adds to existing router, doesn't replace it
class SessionAwareRouter:
    def classify(self, user_query, active_context):
        # Step 1: Existing behavior (abstract's component 2)
        base_classification = self.llm_router.classify(user_query)
        
        # Step 2: NEW — Session context enrichment
        session_insights = self.session_store.get_relevant_history(
            user_id=active_context.user_id,
            query_embedding=self.embed(user_query),
            since=timedelta(days=30)
        )
        
        # Step 3: NEW — Augment classification with history
        if session_insights.recurring_themes:
            base_classification.detected_themes = session_insights.recurring_themes
            base_classification.knowledge_gaps = session_insights.uncaptured_themes
        
        return base_classification
```

**What's different:** The router still does the same classification. It just gets additional context to make a *better* classification.

#### Component 3: SQLite Schema Extension (new table)

Your abstract says: "SQLite for artifact storage." Add one table to the same database:

```sql
-- NEW TABLE in existing SQLite
CREATE TABLE session_history (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    timestamp DATETIME,
    router_classification JSON,      -- SECI mode, reuse situation, selected agent
    user_query TEXT,
    generated_artefacts JSON,        -- List of artefact IDs created
    citations_used JSON,             -- Documents retrieved
    user_feedback JSON,              -- Optional thumbs up/down + notes
    session_embedding BLOB           -- For similarity search
);

-- Indexes for fast queries
CREATE INDEX idx_sessions_user_time ON session_history(user_id, timestamp);
CREATE INDEX idx_sessions_class ON session_history(router_classification);
```

**Why this stays in scope:** Uses the *same* "SQLite for artifact storage" already in your prototype. Not new infrastructure.

#### Component 5: FSM Transition Enhancement (~30 lines)

Your abstract: "The FSM operationalizes the theoretical mapping... and assigns requests to the most appropriate agent state."

Add enrichment rules to the FSM:

```python
# PSEUDOCODE — added to existing FSM transitions
class EnhancedFSMTransitions:
    def determine_next_state(self, classification, user_context):
        # Existing: base FSM decision (abstract's component 5)
        base_state = self.base_fsm.route(classification)
        
        # NEW: Enrich based on session history patterns
        if classification.knowledge_gaps:
            # System has detected recurring uncaptured knowledge
            # → Prioritize externalization
            if classification.seci_mode in ["Socialization", "Externalization"]:
                return AgentState("ScribeAgent", reason="recurring_uncaptured_theme")
        
        if classification.detected_themes:
            # System recognizes related past work
            # → Enhance with context reconstruction
            if classification.reuse_situation in ["shared_work", "similar_task"]:
                return AgentState("ContextReconstructorAgent", 
                                  reason="related_past_sessions_detected")
        
        return base_state
```

**What's different:** Same FSM, same states, same transitions. Just richer transition *conditions* based on accumulated context.

---

## Data Flow (Minimal Change)

```
BEFORE (Abstract's version):
  User → Router(classify) → FSM(assign) → Agent(execute) → Response

AFTER (Session-aware):
  User → Router(classify + session_context) → FSM(assign + enrichment) → Agent(execute) → Response
                                                                                       ↓
                                                                              Store session record
```

**One extra arrow.** That's the entire architectural change.

---

## Evaluation: Fits Your Existing Plan

Your abstract: "The prototype will be assessed in vignette-based scenarios with practitioners... post-task assessment, and qualitative feedback."

**Add these specific items:**

### Quantitative (post-task survey, ~5 questions)
1. "The system seemed to remember my previous interactions" (1-5 Likert)
2. "I did not receive the same artefact twice for similar requests" (1-5 Likert)
3. "The system proactively suggested relevant past work" (1-5 Likert)

### Qualitative (interview probe)
4. "Can you give an example where the system's 'memory' helped or hindered?"
5. "Did the system feel like it was learning from your interactions?"

### Log-based metrics (objective)
6. **Duplicate detection rate:** Count repeated similar requests × same artefact generation
7. **Transition accuracy:** Did FSM enriched-routes match practitioner expectations?

### Baseline condition
- **Control:** Router without session history (your current abstract version)
- **Treatment:** Router with session history (this enhancement)
- Random assignment, crossover design if possible

---

## Why This Stays Within Abstract Scope

| Concern | How Addressed |
|---------|--------------|
| "No new architecture component" | Enhances existing Components 2, 3, 5 |
| "No new theory" | Uses same SECI + Markus; just adds temporal dimension |
| "No new UI" | Transparent to users — effects visible in routing quality |
| "No new storage stack" | Extends existing SQLite; same ChromaDB |
| "DSR evaluation still works" | Adds questions to existing vignette study |
| "Same four agent roles" | Roles unchanged; router just routes better |

**Paper section placement:** Add 1 paragraph to Section 3 (System Design) describing session history enrichment, and 2 sentences to Evaluation describing the context-awareness questions.

---

## Implementation Checklist (2-3 Days)

- [ ] Day 1: Add `session_history` table to SQLite schema
- [ ] Day 1: Modify Router to query session history before classification
- [ ] Day 2: Store session records after each interaction
- [ ] Day 2: Add enrichment rules to FSM transitions
- [ ] Day 2: Write session similarity query (embedding-based)
- [ ] Day 3: Integration test with existing Streamlit UI
- [ ] Day 3: Add evaluation survey questions to vignette protocol

---

## Files

1. **Vision doc (unused):** `ikmas-dreaming-design.md` — the full OpenClaw Dreaming concept
2. **Scoped proposal:** `ikmas-dreaming-geneme-aligned.md` — earlier intermediate version
3. **This file:** `docs/archive/session-awareness-proposal.md` — scoped directly to abstract

---

*Use this file for GeNeMe implementation. Keep vision doc for post-conference.*
