# IKMAS Model Use Case Matrix

## Model Categories and Use Cases

| Category | Model | Response Time | Max Tokens | Primary Use Cases | Performance Notes |
|----------|-------|---------------|------------|------------------|------------------|
| **Audio Speech** | Kokoro-82M | 0.33s | - | Text-to-speech generation | Fast, but limited |
| | tts-1-hd | 0.97s | - | Text-to-speech generation | Slower |
| **Audio Transcription** | openai/whisper-large-v3 | 0.73s | - | Audio-to-text conversion | Reasonable speed |
| **Chat/Generation** | alias-code | 0.28s | 128000 | Code generation, text completion | Fast, high token limit |
| | alias-ha | 0.36s | 40000 | General chat | Moderate speed |
| | alias-huge | 0.84s | 262144 | Complex reasoning | Slower |
| | alias-huge-no-thinking | 0.30s | 262144 | Fast responses | Fast |
| | alias-reasoning | 0.84s | 262144 | Complex reasoning | Slower |
| | alias-vision | 0.14s | 131072 | Vision-language tasks | Fastest |
| | google/gemma-4-31B-it | 0.30s | 200704 | General chat | Fast |
| | meta-llama/Llama-3.1-8B-Instruct | 0.21s | 32768 | General chat | Fast |
| | meta-llama/Llama-3.3-70B-Instruct | 0.23s | 40000 | General chat | Fast |
| | MiniMaxAI/MiniMax-M2.5 | 2.21s | 196608 | General chat | Slow |
| | moonshotai/Kimi-K2.6 | 0.37s | 262144 | General chat | Moderate |
| | openai/gpt-oss-120b | 0.49s | 131072 | General chat | Moderate |
| | openGPT-X/Teuken-7B-instruct-v0.6 | 0.49s | 4096 | General chat | Moderate |
| | Qwen/Qwen3-Coder-30B-A3B-Instruct | 0.10s | 128000 | Code, reasoning | Fastest |
| | Qwen/Qwen3-VL-8B-Instruct | 0.16s | 131072 | Vision-language tasks | Fast |
| **Embedding** | Qwen/Qwen3-Embedding-4B | 0.18s | - | Text embedding | Fastest |
| **Image Generation** | alias-image-generation | 3.52s | - | Image creation | Slow |
| | black-forest-labs/FLUX.2-dev | 4.11s | - | Image creation | Slow |
| | black-forest-labs/FLUX.2-klein-9B | 6.73s | - | Image creation | Slowest |
| | stabilityai/stable-diffusion-3.5-large-turbo | 1.64s | - | Image creation | Fastest among image gen |
| **Rerank** | BAAI/bge-reranker-v2-m3 | 0.12s | - | Document ranking | Fastest |

## Response Time Optimization Recommendations

### Fastest Models for Speed Optimization:
1. **Qwen/Qwen3-Coder-30B-A3B-Instruct** (0.10s) - Best for chat generation
2. **Qwen/Qwen3-Embedding-4B** (0.18s) - Best for embeddings  
3. **BAAI/bge-reranker-v2-m3** (0.12s) - Best for reranking
4. **alias-vision** (0.14s) - Fast vision-language processing
5. **Qwen/Qwen3-VL-8B-Instruct** (0.16s) - Fast vision-language processing

### Key Areas for Response Time Improvement:
1. **Embedding Operations**: Use Qwen/Qwen3-Embedding-4B for faster text embedding
2. **Reranking**: Use BAAI/bge-reranker-v2-m3 for quick document ranking
3. **Chat Generation**: Consider Qwen/Qwen3-Coder-30B-A3B-Instruct or alias-huge-no-thinking for speed
4. **Caching**: Implement caching for frequently processed embeddings and rerankings
5. **Batch Processing**: Batch embedding operations for multiple documents to reduce overhead