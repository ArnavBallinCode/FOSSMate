# FOSSMate Roadmap

## Vision

Provide an installable AI maintainer assistant that helps open-source projects handle triage, onboarding, and repository Q&A with minimal manual overhead.

## Phase 1: Foundation (Current)

- FastAPI backend scaffold
- Config system and validation
- Webhook ingestion + signature verification
- Async DB persistence
- Pluggable LLM provider interface

## Phase 2: Maintainer Automation

- `issues.opened`: concise issue summaries
- Automatic label suggestions
- `issue_comment.created`: onboarding reply for contributor intent
- `pull_request.opened`: PR summary

## Phase 3: Repository Intelligence (RAG)

- Repo ingestion for code/docs
- Structured chunking by file and symbol
- Embedding generation + Qdrant indexing
- Retrieval with source references

## Phase 4: Production Readiness

- Dedicated background workers
- Retries and dead-letter strategy
- Telemetry and tracing
- Multi-tenant installation configuration
- Integration tests + CI

## Stretch Goals

- Auto-generated release notes
- AI-assisted stale issue management
- Maintainer triage dashboards
- Fine-grained per-repo policy prompts
