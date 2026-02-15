# FOSSMate

FOSSMate is an open-source GitHub App backend that helps maintainers triage issues, support contributors, and answer repository questions with retrieval-augmented context.

## OSS-First Core Principle

FOSSMate core functionality is designed to run without closed-source APIs.

Core stack:

- FastAPI backend
- SQLite/Postgres metadata store
- Qdrant vector store
- Ollama/local or self-hosted inference endpoints

Proprietary model APIs (Gemini/OpenAI) are supported only as optional adapters for MVP experimentation. They are not required for the architecture, deployment model, or roadmap.

## Project Status

`MVP scaffold` with production-oriented structure.

Implemented now:

- GitHub webhook ingestion with signature verification
- Persistent webhook event storage
- Provider abstraction layer (`LLMProvider`)
- Async FastAPI + SQLAlchemy foundation

Planned next:

- Real issue/PR automation handlers
- Ingestion + chunking + indexing
- RAG answers with source references
- Worker queue and reliability controls

## How It Works

```mermaid
flowchart LR
  A[GitHub Webhook] --> B[Verify Signature]
  B --> C[Persist Event]
  C --> D[Background Worker]
  D --> E[Retriever Qdrant]
  D --> F[Inference Provider]
  D --> G[GitHub Comment or Label Action]
```

## Repository Layout

```text
.
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── test_llm.py
├── docs/
├── scripts/
│   └── setup_github_app.py
├── .env.example
├── docker-compose.yml
└── README.md
```

## Quick Start (Self-Hosted)

```bash
git clone https://github.com/Zenkai-src/FOSSMate.git
cd FOSSMate
conda create -n fossmate python=3.11 -y
conda activate fossmate
pip install -r backend/requirements.txt
cp .env.example .env
```

Run API:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Default Open-Source Inference Path

Default configuration uses local Ollama (no proprietary API dependency):

```env
LLM_PROVIDER=ollama
LLM_ENDPOINT=http://localhost:11434
LLM_MODEL_NAME=llama3.1
```

Pull model locally:

```bash
ollama pull llama3.1
```

## Optional Proprietary Adapters (Not Required)

You can optionally use Gemini/OpenAI/custom OpenAI-compatible endpoints for MVP speed:

- `LLM_PROVIDER=gemini`
- `LLM_PROVIDER=openai`
- `LLM_PROVIDER=custom`

These are adapters only; core architecture remains provider-independent.

## GitHub App Setup (Actual Repositories)

Generate checklist:

```bash
python scripts/setup_github_app.py --print-checklist
```

In GitHub App settings:

- Webhook URL: `https://<public-domain>/webhooks/github`
- Webhook secret: exact `GITHUB_WEBHOOK_SECRET` value from `.env`

Recommended permissions:

- Issues: Read & write
- Pull requests: Read & write
- Contents: Read-only
- Metadata: Read-only

Recommended events:

- Issues
- Issue comment
- Pull request
- Installation
- Installation repositories

Install app on target repos, then open an issue/PR to trigger webhook flow.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `APP_ENV` | No | `development`, `staging`, `production` |
| `LOG_LEVEL` | No | Logging level |
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Yes | GitHub App private key |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook signature secret |
| `LLM_PROVIDER` | Yes | `ollama`, `custom`, `gemini`, `openai` |
| `LLM_MODEL_NAME` | Yes | Model name |
| `LLM_ENDPOINT` | Depends | Required for `ollama/custom` |
| `LLM_API_KEY` | Depends | Required for `gemini/openai/custom` |
| `LLM_EMBEDDING_MODEL` | No | Embedding model identifier |
| `QDRANT_URL` | No | `in-memory` or Qdrant URL |
| `DATABASE_URL` | No | SQLAlchemy async DB URL |

## Current Endpoints

- `GET /health`
- `POST /webhooks/github`
- `POST /webhooks/github/test`
- `GET /chat/ping`
- `GET /admin/ping`

## Roadmap Docs

- `docs/ROADMAP.md`
- `docs/OPERATING_MODEL.md`

## Contributing

See `CONTRIBUTING.md`.

## License

MIT (`LICENSE`).
