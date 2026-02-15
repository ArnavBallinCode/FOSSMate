# FOSSMate Operating Model

## Core Guarantee

FOSSMate core automation and retrieval path must run on open/self-hosted infrastructure.

Required core services:

- GitHub App webhook endpoint
- Async processing layer
- SQL metadata store
- Qdrant vector store
- Local or self-hosted inference (default: Ollama)

## Adapter Policy

- Proprietary providers are optional adapters.
- No core feature should be blocked on Gemini/OpenAI availability.
- Adapter-specific logic should remain isolated in provider classes.

## Event Lifecycle

1. GitHub sends event to `/webhooks/github`.
2. Signature verified with webhook secret.
3. Payload persisted to `webhook_events`.
4. Background handler processes event.
5. Handler retrieves context (when indexed) from Qdrant.
6. Inference provider generates output.
7. Response is posted to GitHub and outcome persisted.

## Maintainer Experience

- Install app on repository.
- Keep normal issue/PR workflow.
- Receive summaries, suggestions, and onboarding guidance automatically.
- Tune behavior via installation-level config (planned).
