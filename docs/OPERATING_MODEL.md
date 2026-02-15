# FOSSMate Operating Model

This document explains how FOSSMate is expected to run in real repositories.

## Deployment Modes

1. Single-tenant self-hosted:
   - One team hosts one FOSSMate instance for its repos.
2. Multi-tenant self-hosted:
   - One instance serves multiple GitHub App installations.
3. Managed SaaS (future):
   - Hosted FOSSMate with onboarding and billing.

## Core Runtime Components

- API server:
  - receives webhook events
  - verifies signatures
  - stores events
- Processing layer:
  - asynchronous task execution for summaries/comments/indexing
- Data stores:
  - SQL metadata/event history
  - vector store for retrieval context
- LLM layer:
  - provider abstraction with runtime provider selection

## Event Lifecycle (Planned)

1. GitHub sends event -> `/webhooks/github`.
2. Event validated and persisted.
3. Worker picks event and maps to handler.
4. Handler prepares prompt + retrieval context (if needed).
5. LLM response is post-processed and policy-filtered.
6. GitHub API posts comment/label updates.
7. Outcome saved for auditability.

## Safety and Governance

- Signatures validated for all webhook requests.
- Minimal GitHub permissions should be enforced.
- Installation-level config controls behavior per repository.
- Store only required metadata/content slices.
- Keep an audit trail of inbound events and outbound actions.

## What Repo Maintainers Experience

- Install app on repository.
- Open an issue or PR as usual.
- FOSSMate posts summary and actionable guidance.
- Contributor asks to work on issue -> onboarding response appears.
- Team can tune behavior through config (future admin endpoints).
