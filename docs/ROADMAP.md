# FOSSMate Roadmap

## Phase 1 (Completed Foundations)

- FastAPI backend scaffold
- GitHub webhook verification and normalization
- Async queue + worker boundary
- Database persistence for deliveries and review artifacts
- LLM abstraction with provider adapters

## Phase 2 (Current Core Automation)

- `issues.opened`: summary + label suggestion/apply path
- `issue_comment.created`: onboarding intent reply
- `pull_request.opened` and `pull_request.synchronize`: summaries, suggestions, advisory scoring
- PR comment publishing
- Check Run publishing path (permission-dependent)

## Phase 3 (Near-Term)

- RAG ingestion hardening (`README`, `CONTRIBUTING`, code/docs chunking)
- source-grounded responses with references
- stronger retries/backoff and dead-letter behavior
- installation-level policy controls

## Phase 4 (Scale + Productization)

- durable queue backend
- observability (metrics/traces/delivery dashboards)
- policy templates for organizations
- managed deployment runbooks and SLOs

## Optional Adapter Track

- Keep Gemini/OpenAI/OpenRouter/custom adapters for flexibility
- Ensure OSS provider path remains first-class

## Post-Stabilization Expansion

- GitLab adapter (deferred until GitHub path is production-stable)
- email reporting and developer evaluation workflows
