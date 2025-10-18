# Football RAG Intelligence

A RAG (Retrieval-Augmented Generation) system for football data analysis and insights.

## Overview

This project implements a football intelligence system using RAG architecture to provide insights and answer questions about football data, players, teams, and match statistics.

## Features

- Football data ingestion and processing
- Vector-based document storage and retrieval
- LLM-powered question answering
- Performance monitoring and evaluation

## Inspired by

This codebase has been inspired by:
- [LLMOps Python Package](https://github.com/callmesora/llmops-python-package)
- [AI Tutor Skeleton](https://github.com/towardsai/ai-tutor-skeleton/tree/main)





# With coverage
uv run pytest --cov=src/football_rag
```

## 📈 Performance

Typical response times:

| Stage | Time |
|-------|------|
| Vector search (5 docs) | ~150ms |
| LLM generation | ~800ms (Ollama), ~2s (API) |
| Faithfulness validation | ~50ms |
| **Total** | **~1-3s** |

## 🔧 Configuration

Environment variables (optional, defaults provided):

```bash
# Database
CHROMA_HOST=localhost
CHROMA_PORT=8000
MINIO_ENDPOINT=localhost:9000

# Models
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=smollm2:360
TEMPERATURE=0.1

# Prompts
PROMPT_PROFILE=profile_football_v1

# Performance
LLM_TIMEOUT_MS=120000
CACHE_TTL_S=120
DEFAULT_TOP_K=5
```

## 🐛 Troubleshooting

### "Ollama not running"
```bash
# Start Ollama
ollama serve

# In another terminal, pull model if needed
ollama pull smollm2:360
```

### "ChromaDB connection refused"
```bash
# Start Docker services
docker compose up -d

# Or use remote ChromaDB instance
export CHROMA_HOST=your-remote-host
```

### "Invalid API key"
- Verify key is correct (no extra spaces)
- Check key has required permissions
- Some keys may have usage limits

## 📚 Data Sources

This system uses:
- **Eredivisie 2024-2025:** Dutch top division
- **Match Event Data:** xG, shots, possession, passing accuracy, tackles, interceptoons

Sourced from: WhoScored, Fotmob.

## 🏗️ Project Structure

```
football-rag-intelligence/
├── app.py                          # HF Spaces entry point
├── src/football_rag/
│   ├── api/
│   │   └── app.py                 # Gradio + FastAPI interface
│   ├── core/
│   │   ├── prompts_loader.py      # Load prompts from YAML
│   │   ├── metrics.py             # Request/latency tracking
│   │   ├── middleware.py          # Observability middleware
│   │   └── logging.py             # Structured logging
│   ├── llm/
│   │   └── generate.py            # Multi-provider LLM generation
│   ├── models/
│   │   └── rag_pipeline.py        # Main RAG orchestration
│   ├── storage/
│   │   └── vector_store.py        # ChromaDB wrapper
│   └── data/
│       ├── ingestion.py           # Data pipeline
│       └── scrapers.py            # Web scrapers
├── prompts/
│   └── profile_football_v1.yml    # System/user prompts
├── tests/
│   ├── core/
│   ├── api/
│   └── models/
├── pyproject.toml                  # Dependencies
└── docker-compose.yml              # Services
```

## 🚀 Deployment

### Deploy to Hugging Face Spaces

1. Create a new Space: [huggingface.co/new-space](https://huggingface.co/new-space)
   - SDK: Docker or Gradio
   - Visibility: Public (for demo)

2. Connect your GitHub repo

3. Add secrets in Space settings:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY` (optional)
   - `GEMINI_API_KEY` (optional)

4. Space will auto-deploy from GitHub

5. Share your Space URL

### Local Deployment

```bash
# Build Docker image
docker build -t football-rag .

# Run container
docker run -p 7860:7860 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  football-rag
```

## 📖 How RAG Works

**Traditional LLM:**
```
User Question → LLM → Generated Answer
```

**RAG System:**
```
User Question →
  ├─ Retrieve: Search vector DB for relevant documents
  ├─ Augment: Add retrieved documents as context
  ├─ Generate: LLM answers with grounded context
  └─ Validate: Check if answer matches source documents
    → Faithful Answer + Confidence Score + Source Documents
```

## Acknowledgments

Built for the Full Stack AI Engineering course of Towards AI as capstone project, fulfilling obligatory and optional requirements for final certification:

- ✅ **RAG System:** Full retrieval + generation pipeline
- ✅ **LLM Integration:** Multi-provider support (API + local)
- ✅ **HF Spaces Deployment:** Public Space with live demo
- ✅ **Data Pipeline:** Web scraping, ingestion, validation
- ✅ **README Documentation:** Complete with cost estimation
- ✅ **API Key Security:** No hardcoded keys, user input only
- ✅ **Cost < $0.50:** Verified pricing for all providers
- ✅ **5+ Optional Features:** Anti-hallucination, caching, multi-provider, evaluation, observability
- ✅ **Reproducible:** All code and data in version control

## 📝 License

MIT License - See LICENSE file

Inspired by:
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [ChromaDB Vector Database](https://www.trychroma.com/)
- [Gradio Framework](https://www.gradio.app/)

## 📧 Support

Questions or issues?
- Open an issue on GitHub
- Check existing documentation
- Review course materials

---

This codebase has been inspired by:
- [LLMOps Python Package](https://github.com/callmesora/llmops-python-package)
- [AI Tutor Skeleton](https://github.com/towardsai/ai-tutor-skeleton/tree/main)
