# Tutor FSM (Finite State Machine)

This document describes the tutoring state machine used by the system to guide learning interactions.

The FSM is only active for the `TutoringAgent`.

---

## Overview

The Tutor FSM models a structured learning loop:

```
ASSESS → EXPLAIN → CHECK → PRACTICE → FEEDBACK → SCHEDULE → (repeat)
```

It ensures that the system:

- diagnoses user knowledge
- explains concepts
- verifies understanding
- enables practice
- provides feedback
- schedules reinforcement

---

## Activation Rules

The FSM is activated only if:

- `role == "TutoringAgent"`
  OR
- `force_tutor_mode == True`

Otherwise:

```
state = None
```

---

## Initial State Logic

If no previous state exists:

```
current_state = None
```

Then:

- if `retrieval_confidence >= 0.75`
  → start in `EXPLAIN`
- else
  → start in `ASSESS`

---

## State Definitions

### ASSESS

Purpose:

- Diagnose user's current understanding
- Clarify the learning goal

Typical behavior:

- Ask 2–3 diagnostic questions
- Identify gaps

---

### EXPLAIN

Purpose:

- Provide a structured explanation

Typical behavior:

- Clear, concise explanation
- Adapted to user level

---

### CHECK

Purpose:

- Verify understanding

Typical behavior:

- Ask comprehension questions
- Require user to explain concepts

---

### PRACTICE

Purpose:

- Apply knowledge

Typical behavior:

- Exercises
- Small tasks
- Problem-solving

---

### FEEDBACK

Purpose:

- Reinforce or correct understanding

Typical behavior:

- Highlight mistakes
- Confirm correct reasoning
- Suggest improvements

---

### SCHEDULE

Purpose:

- Support long-term learning

Typical behavior:

- Suggest review timing
- Reinforce spaced repetition

---

## Transition Logic

### Initial

```
None → EXPLAIN (if confidence ≥ 0.75)
None → ASSESS (otherwise)
```

---

### Main Transitions

```
ASSESS   → EXPLAIN
EXPLAIN  → CHECK
```

---

### Conditional Transitions

```
CHECK → PRACTICE    if answered_check == True
CHECK → CHECK       if answered_check == False
```

```
PRACTICE → FEEDBACK if practice_done == True
PRACTICE → PRACTICE if practice_done == False
```

---

### Final Transitions

```
FEEDBACK → SCHEDULE
SCHEDULE → ASSESS   (loop restart)
```

---

## Session Context Variables

The FSM depends on values stored in `session_ctx`:

- `state`
   - current FSM state
- `answered_check` (bool)
   - whether the user answered the check question
- `practice_done` (bool)
   - whether the practice task is completed

---

## Default Behavior

If an unknown or invalid state occurs:

```
→ fallback to ASSESS
```

---

## Design Principles

### Deterministic

- Same inputs → same state transitions

### Structured Learning

- Enforces pedagogical sequence
- Prevents skipping key steps

### Adaptive Entry

- High confidence → skip diagnosis
- Low confidence → start with assessment

### Loop-Based Learning

- Learning cycle repeats for reinforcement

---

## Limitations (Iteration 1)

- No adaptive difficulty
- No mastery tracking yet
- No personalization
- Binary signals only (`answered_check`, `practice_done`)
- No multi-topic handling

---

## Future Improvements

### Iteration 2

- mastery score integration
- dynamic transitions based on performance
- better session state tracking

### Iteration 3

- personalized learning paths
- spaced repetition scheduling
- adaptive difficulty levels

---

## Summary

The Tutor FSM provides a structured learning loop that transforms the system from:

→ simple Q&A

into:

→ guided learning experience

It is a core component of the `TutoringAgent` and enables:

- active learning
- feedback loops
- knowledge internalization
