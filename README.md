# FOSSMate

FOSSMate is an open-source GitHub App that helps maintainers with issue triage, contributor onboarding, PR summaries, and review suggestions.

Core promise:
- Install the app on a repository.
- FOSSMate runs on webhook events.
- Maintainers get automated comments/labels/review output.

## Current Status

Working now:
- GitHub App authentication (JWT + installation tokens)
- Webhook verification + idempotent delivery logging
- Async event processing queue
- `issues.opened`: issue summary + label suggestions + label apply attempt
- `issue_comment.created`: onboarding intent detection + maintainer-ready reply
- `pull_request.opened` and `pull_request.synchronize`: PR summary + per-file summaries + suggestions + advisory score
- PR review comment posting
- SQLite persistence for events, runs, findings, and scores
- Multi-provider LLM abstraction (Ollama default, Gemini/OpenAI/OpenRouter/custom adapters)

In progress:
- Check Run publishing depends on GitHub App `Checks: Read and write` permission
- RAG ingestion/retrieval production hardening
- Advanced reporting and reliability controls

## Documentation

Start here if you are new:
- [Beginner Setup Guide](docs/GETTING_STARTED.md)

How the system works internally:
- [Working Logic and Architecture](docs/WORKING_LOGIC.md)

Additional docs:
- [Operating Model](docs/OPERATING_MODEL.md)
- [Roadmap](docs/ROADMAP.md)
- [Screenshots Guide](docs/SCREENSHOTS.md)

## Quick Start (Conda + Local)

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

## Required GitHub App Permissions

- Issues: Read and write
- Pull requests: Read and write
- Checks: Read and write
- Contents: Read-only
- Metadata: Read-only

Required webhook events:
- Issues
- Issue comment
- Pull request
- Installation
- Installation repositories

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Yes* | Inline private key PEM |
| `GITHUB_PRIVATE_KEY_PATH` | Yes* | Path to `.pem` file (recommended) |
| `GITHUB_WEBHOOK_SECRET` | Yes | Secret used for signature verification |
| `GITHUB_TOKEN` | No | Local fallback only (not recommended for production) |
| `LLM_PROVIDER` | Yes | `ollama`, `gemini`, `openai`, `openrouter`, `custom`, `azure_openai`, `deepseek`, `deepseek_r1` |
| `LLM_MODEL_NAME` | Yes | Model name |
| `LLM_ENDPOINT` | Depends | Needed for `ollama/custom` and some adapters |
| `LLM_API_KEY` | Depends | Needed for provider APIs |
| `DATABASE_URL` | No | SQLAlchemy async DB URL |
| `QDRANT_URL` | No | `in-memory` or qdrant URL |
| `QUEUE_WORKERS` | No | Number of async queue workers |
| `FEATURE_PR_SUMMARY` | No | Enable PR summary generation |
| `FEATURE_FILE_SUMMARY` | No | Enable per-file summaries |
| `FEATURE_REVIEW_SUGGESTIONS` | No | Enable review suggestions |
| `FEATURE_SCORING` | No | Enable advisory scoring |
| `FEATURE_COMMIT_TRIGGER` | No | Re-run on PR synchronize events |
| `FEATURE_GITLAB` | No | Enables `/webhooks/gitlab` endpoint |

\* Use either `GITHUB_PRIVATE_KEY` or `GITHUB_PRIVATE_KEY_PATH`.

## Helpful Script

Print a setup checklist from local `.env`:

```bash
python scripts/setup_github_app.py --print-checklist
```

## Screenshot Policy

Use `docs/SCREENSHOTS.md` for required capture list, naming, and redaction rules.

## API Endpoints

- `GET /health`
- `POST /webhooks/github`
- `POST /webhooks/github/test`
- `GET /chat/ping`
- `POST /chat/ask`
- `GET /admin/ping`
- `GET /admin/installations/{id}/status`
- `POST /admin/installations/{id}/replay/{event_id}`
- `GET /reports/developer-evaluation`

Optional:
- `POST /webhooks/gitlab` (when `FEATURE_GITLAB=true`)

## License

MIT (`LICENSE`).
