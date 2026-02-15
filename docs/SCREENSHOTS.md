# Screenshots Guide

Use this guide to keep documentation screenshots consistent and beginner-friendly.

## Required Screenshots

Save screenshots under `docs/screenshots/` with these exact names:

1. `github-app-permissions.png`
- GitHub App repository permissions page
- Must clearly show:
  - Issues: Read and write
  - Pull requests: Read and write
  - Checks: Read and write
  - Contents: Read-only
  - Metadata: Read-only

2. `github-app-events.png`
- GitHub App webhook event subscriptions
- Must clearly show enabled events:
  - Issues
  - Issue comment
  - Pull request
  - Installation
  - Installation repositories

3. `github-app-webhook.png`
- GitHub App webhook settings section
- Must show webhook URL field and secret state

4. `health-endpoint.png`
- Browser or terminal output showing `/health` response after startup

## Capture Rules

- Redact all secrets/tokens before saving.
- Keep full browser width so labels are readable.
- Prefer light mode for readability in docs.
- Use PNG format.
- Replace older screenshots when UI changes.

## Markdown Snippets

Use these snippets when embedding:

```md
![GitHub App Permissions](docs/screenshots/github-app-permissions.png)
![GitHub App Events](docs/screenshots/github-app-events.png)
![GitHub App Webhook](docs/screenshots/github-app-webhook.png)
![FOSSMate Health Endpoint](docs/screenshots/health-endpoint.png)
```
