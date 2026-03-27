# Intent & Distance Classification (Iteration 1)

This document defines the rule-based classification used to map user input to:

- **Intent** (what the user wants)
- **Knowledge Distance** (Markus reuse types)

This version uses simple keyword matching for deterministic and testable behavior.

---

## Overview

Pipeline:

```
User Input
    ↓
Intent Classification (keywords)
    ↓
Distance Estimation (rules)
```

---

# Intent Classification

The system classifies each user query into exactly one intent.

## 1. learn_mode

Triggered when the user explicitly wants to learn, practice, or be tested.

**Keywords:**

- lern
- prüf mich
- quiz
- üb
- frage mich ab

**Examples:**

- „Prüf mich zu Mikroökonomie“
- „Gib mir ein Quiz“
- „Ich will das lernen“

---

## 2. what_is

Triggered when the user asks for definitions or explanations.

**Keywords:**

- was ist
- erkläre
- definition
- bedeutet

**Examples:**

- „Was ist ein Nash-Gleichgewicht?“
- „Erkläre mir Angebot und Nachfrage“

---

## 3. simplify

Triggered when the user asks for simpler explanations.

**Keywords:**

- einfach
- vereinfacht
- verständlich
- für anfänger

**Examples:**

- „Erklär das einfach“
- „Mach das verständlich“

---

## 4. project_specific

Triggered when the user refers to their own project or internal context.

**Keywords:**

- in unserem projekt
- bei uns
- unsere doku
- unsere dateien

**Examples:**

- „Wie haben wir das im Projekt gelöst?“
- „Was steht in unserer Doku dazu?“

---

## 5. cross_context

Triggered when the user asks about other teams or general best practices.

**Keywords:**

- wie machen andere
- best practice
- vergleich mit anderen

**Examples:**

- „Wie machen andere Teams das?“
- „Was sind Best Practices?“

---

## 6. pattern_mining

Triggered when the user wants patterns, trends, or abstraction.

**Keywords:**

- muster
- cluster
- analysiere
- finde konzepte
- signal

**Examples:**

- „Finde Muster in diesen Daten“
- „Welche Konzepte tauchen hier auf?“

---

## Default Behavior

If no keyword matches:

→ fallback intent:

```
what_is
```

---

# Distance Estimation

Distance is derived from intent and specific phrases.

## ESN (Expertise-Seeking Novice)

Triggered when:

- intent is:
   - what_is
   - simplify
   - learn_mode

**Meaning:**

User seeks understanding outside their expertise.

---

## SWP (Shared Work Producer)

Triggered when input contains:

- „in unserem projekt“
- „unsere dateien“

**Meaning:**

User refers to their own project or prior work.

---

## SWPr (Shared Work Practitioner)

Triggered when input contains:

- „wie machen andere“
- „andere teams“

**Meaning:**

User compares with peers in similar roles.

---

## SKM (Secondary Knowledge Miner)

Triggered when:

- intent = pattern_mining

**Meaning:**

User searches for abstract patterns or insights.

---

## Default Behavior

If no rule applies:

```
ESN
```

---

# Design Principles

## Deterministic

- Same input → same output
- No randomness

## Transparent

- Every classification can be traced to a keyword

## Testable

- Easy to write unit tests for each rule

## Fast

- No external models required

---

# Limitations (Iteration 1)

- No synonym detection
- No paraphrase understanding
- No multi-intent handling
- Sensitive to exact wording
- No context awareness across turns
