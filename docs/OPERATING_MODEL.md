# FOSSMate Operating Model

## Product Modes

FOSSMate is designed for two operating modes:

1. Managed deployment
- End users install the GitHub App.
- FOSSMate is hosted and maintained by operators.
- No local infrastructure needed for maintainers.

2. Self-hosted deployment
- Teams run backend and infrastructure themselves.
- Same webhook/event model, different hosting ownership.

## Core Principle

Core functionality must remain available on OSS infrastructure:
- FastAPI backend
- SQLite/Postgres metadata store
- Qdrant vector store
- Ollama/local or self-hosted inference endpoints

Proprietary APIs are optional adapters, not architectural dependencies.

## Runtime Responsibilities

- Validate and ingest webhooks
- Normalize events and queue processing
- Execute issue/PR automation logic
- Write results back to GitHub (comments, labels, checks)
- Persist operational records for replay/audit/reporting

## Security Model

- GitHub App JWT + installation token flow is default auth path
- Webhook signatures are required
- Secrets are env-managed; never hardcoded
- Private key files (`.pem`) must be excluded from version control

## Reliability Model

- Idempotency keys prevent duplicate work
- Delivery state machine: `queued -> processing -> done/failed`
- Replay endpoints support recovery from transient failures
- Feature flags support staged rollout per installation

## Maintainer Experience Goal

A maintainer should:
1. Install the app
2. Continue normal issue/PR workflow
3. Receive automated triage and review assistance with minimal setup friction
