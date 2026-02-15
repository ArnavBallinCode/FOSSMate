# Contributing to FOSSMate

Thanks for contributing.

## Local Setup

1. Create env and install dependencies:

```bash
conda create -n fossmate python=3.11 -y
conda activate fossmate
pip install -r backend/requirements.txt
```

2. Configure local environment:

```bash
cp .env.example .env
```

3. Run backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## Development Guidelines

- Keep services async-first.
- Add type hints for public functions/classes.
- Keep provider integrations behind abstractions (`LLMProvider`).
- For webhook work, keep request path fast and defer heavy work to background/queue.
- Add tests for event parsing, signature verification, and persistence.

## Suggested Workflow

1. Create a branch from `main`.
2. Make focused changes.
3. Run local checks:
   - `python -m compileall backend/app backend/test_llm.py`
   - smoke test endpoint(s)
4. Open a PR with:
   - behavior summary
   - screenshots/logs for webhook tests
   - risks and follow-up items

## Areas Needing Help

- GitHub App auth (`utils/github_auth.py`)
- Ingestion + chunking implementation
- Qdrant integration and retrieval ranking
- RAG answer formatting with source references
- End-to-end tests and CI
