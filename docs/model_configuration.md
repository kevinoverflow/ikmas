# IKMAS Agent-Specific Model Configuration

This file contains the model configuration for different agents in the IKMAS system.

## Model Selection Strategy

Based on the decision rules provided, each agent uses the most appropriate model:

### Router
- Primary: MiniMax-M2.5 (fast, structured responses)
- Fallback: Llama 4 Scout (for large contexts)

### Scribe Agent
- Primary: MiniMax-M2.5 (speed/quality balance for documentation)
- Fallback: Llama 4 Scout (for long transcripts)

### Semantic Linking Agent
- Primary: Kimi-K2.5 (strong reasoning for linking)
- Fallback: Llama 4 Scout (for large corpora)

### Mentor Agent
- Primary: Kimi-K2.5 (best explanation quality)
- Fallback: MiniMax-M2.5 (for speed in interactive mode)

### Context Reconstructor Agent
- Primary: Kimi-K2.5 (best inference for reconstruction)
- Fallback: Llama 4 Scout (for very long artifacts)

### General LLM
- Primary: Qwen/Qwen3-Coder-30B-A3B-Instruct (high-quality responses)

## Environment Variables

You can override the default models using these environment variables:

- ROUTER_MODEL_NAME
- SCRIBE_MODEL_NAME  
- SEMANTIC_LINKING_MODEL_NAME
- MENTOR_MODEL_NAME
- CONTEXT_RECONSTRUCTOR_MODEL_NAME
- LANGUAGE_MODEL_NAME