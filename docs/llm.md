# LLM

## Overview

The LLM layer in this system is responsible for **controlled interaction with the language model**.

It is split into two components:

- **`OpenAIChatBackend` (infrastructure)** → handles API communication
- **`LLMClient` (backend)** → enforces strict JSON behavior (validation, repair, fallback)

---

## Architecture

```
Orchestrator
   ↓
LLMClient (JSON logic)
   ↓
OpenAIChatBackend (API call)
   ↓
OpenAI API
```

---

## Design Goal

> Ensure that **every LLM response is valid, structured, and safe to use in the system**.

---

# 🔧 Components

## 1. OpenAIChatBackend

**Location:** `app/infrastructure/llm.py`

### Responsibility

- Initialize OpenAI client
- Send prompts to the model
- Return raw text output

### Key Method

```
defgenerate(prompt:str) ->str
```

### Example

```
backend=OpenAIChatBackend()
response=backend.generate("Explain RAG simply.")
```

### Characteristics

- Minimal logic
- No validation
- No schema awareness
- No fallback handling

---

## 2. LLMClient

**Location:** `app/backend/llm_client.py`

### Responsibility

- Call the backend
- Enforce **strict JSON output**
- Validate against schema
- Attempt repair if invalid
- Fallback if repair fails

---

# 🔄 Execution Flow

## 1. Generate Output

```
raw=backend.generate(prompt)
```

---

## 2. Validate JSON

```
payload=parse_and_validate_json(raw)
```

If valid:

```
returnpayload
```

---

## 3. Repair (if invalid)

```
repair_json(raw)
```

- Sends original output back to the model
- Requests corrected JSON
- Validates again

---

## 4. Fallback (if repair fails)

```
returnfallback_payload(...)
```

This guarantees:

> ❗ The system NEVER returns invalid output

---

# 🧠 Why Strict JSON?

Traditional LLM usage:

```
LLM → free text → parse manually → hope it works
```

This system:

```
LLM → JSON → validate → repair → fallback
```

Benefits:

- Deterministic behavior
- No parsing errors
- Safe for UI + storage
- Enables automation (FSM, artefacts, etc.)

---

# 📦 Output Contract

The LLM must return a JSON object with:

```
{
  "role":"...",
  "state":"...",
  "assistant_message":"...",
  "questions": [],
  "artefacts": [],
  "actions": [],
  "citations": [],
  "telemetry": {}
}
```

### Rules

- No additional fields
- No markdown fences
- No explanations outside JSON
- `state` must be valid enum or null

---

# 🔁 Repair Strategy

If the model output is invalid:

1. Send original output back to model
2. Ask for corrected JSON
3. Validate again

Example instruction:

```
Repair the following output into valid JSON.
Return JSON only.
Do not include explanations.
```

---

# 🧯 Fallback Strategy

If repair fails:

- Return deterministic fallback JSON
- Usually:
   - `role = TutoringAgent`
   - `state = ASSESS`
   - 2–3 clarifying questions

---

# 📊 Telemetry Fields

Every response includes:

```
{
  "repair_used":true |false,
  "fallback_used":true |false
}
```

This allows:

- debugging
- monitoring model reliability
- evaluating prompt quality

---

# ⚠️ Failure Modes Handled

| Problem                 | Solution             |
| ----------------------- | -------------------- |
| Invalid JSON            | Repair               |
| Broken schema           | Repair               |
| Missing fields          | Repair               |
| Totally unusable output | Fallback             |
| Empty response          | Exception → fallback |
