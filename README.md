<div align="center">

# GitHub for Telegram

**A GitHub control center built for Telegram.**

Manage repositories, branches, files, commits, pull requests, reviews and repository notifications without leaving Telegram.

<p>
  <img src="https://i.ibb.co/WWS60dJP/tmp-otmadsf.jpg" alt="GitHub for Telegram preview" width="850">
</p>

</div>

---

## Overview

GitHub for Telegram brings practical GitHub repository management into a focused Telegram interface.

It combines a Telegram bot, GitHub OAuth, GitHub App authentication, FastAPI webhooks, MongoDB and Redis into one service.

The goal is simple: **browse, review and manage GitHub work from Telegram without turning the bot into a noisy dashboard.**

## Features

| Area | Features |
| --- | --- |
| Repositories | Browse, search and open repository dashboards |
| Source | Browse branches, directories and files |
| Files | Read and edit file contents |
| Commits | Review changes and create commits from Telegram |
| Pull requests | View PRs, files, commits and reviews |
| PR reviews | Approve, request changes or leave review comments |
| PR lifecycle | Merge, close, reopen and move drafts to review |
| Integrations | Connect repositories for GitHub event notifications |
| Notifications | Push, PR, issue, release, Actions and star events |
| Replies | Reply to supported GitHub notifications from Telegram |
| Authentication | GitHub OAuth with PKCE and encrypted token storage |
| Web service | FastAPI health, OAuth callback and webhook receiver |
| Sessions | Redis-backed editing and review sessions |

## Commands

~~~text
/start
/connect
/repos

/newintegration owner/repository
/listintegrations
/delintegration repository_id
~~~

### /connect

Starts the GitHub OAuth authorization flow with PKCE.

### /repos

Opens the repository browser and repository-level management interface.

### /newintegration

Creates a repository webhook and connects GitHub events to your Telegram account.

~~~text
/newintegration owner/repository
~~~

### /listintegrations

Lists repositories currently connected to Telegram notifications.

### /delintegration

Removes a repository integration and its configured webhook.

~~~text
/delintegration repository_id
~~~

## Repository control

The repository dashboard provides a single entry point for GitHub data and actions.

~~~text
Repository
├── Files
├── Commits
├── Branches
├── Tags
├── Pull requests
├── Issues
├── Actions
├── Releases
├── Contributors
└── Deployments
~~~

The repository layer communicates directly with the GitHub REST API rather than maintaining a local Git mirror.

## File editing and commits

File editing uses temporary sessions so changes can be reviewed before reaching GitHub.

~~~text
Open file
   ↓
Edit content
   ↓
Review changes
   ↓
Enter commit message
   ↓
Confirm
   ↓
Create Git objects
   ↓
Update branch
~~~

The commit engine builds blobs, trees and commits through the GitHub API and checks the branch head before applying the final reference update.

## Pull requests

Pull requests have their own management interface.

### Review

- Approve
- Request changes
- Submit a review comment
- View existing reviews

### Inspection

- Changed files
- Commit history
- Review history
- Branch information
- Addition/deletion statistics

### Lifecycle

- Merge
- Close
- Reopen
- Move draft PRs to ready for review

Merge requests use the current PR head SHA when possible so an outdated Telegram view does not blindly merge a changed branch.

## GitHub integrations

Repository integrations create GitHub webhooks for supported events.

~~~text
push
pull_request
issues
release
workflow_run
star
~~~

Webhook requests are verified with GitHub’s X-Hub-Signature-256 HMAC signature before processing. GitHub recommends this signature for webhook validation. citeturn0search1turn0search3

Each GitHub delivery ID is stored so duplicate deliveries are not repeatedly forwarded to the same Telegram integration.

## Reply from Telegram

Supported issue and pull-request notifications can be replied to directly.

~~~text
GitHub notification
        ↓
Reply in Telegram
        ↓
GitHub issue / pull request comment
~~~

## Architecture

~~~text
                    ┌─────────────────────┐
                    │       Telegram      │
                    │   Bot / Inline UI   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Kurigram       │
                    │    Bot Handlers     │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      ┌────────────┐    ┌────────────┐    ┌────────────┐
      │  GitHub    │    │   Redis    │    │  MongoDB   │
      │ REST / App │    │  Sessions  │    │  Storage   │
      └──────┬─────┘    └────────────┘    └────────────┘
             │
             ▼
      ┌─────────────────┐
      │     FastAPI     │
      │ OAuth / Webhook │
      └─────────────────┘
~~~

## Project structure

~~~text
Github/
├── github/
│   ├── auth.py
│   ├── client.py
│   ├── commit.py
│   ├── errors.py
│   ├── oauth.py
│   └── repositories.py
│
├── handlers/
│   ├── commits.py
│   ├── files.py
│   ├── integrations.py
│   ├── oauth.py
│   ├── pulls.py
│   ├── replies.py
│   ├── repos.py
│   └── start.py
│
├── app.py
├── bot.py
├── buttons.py
├── config.py
├── state.py
├── storage.py
└── web.py
~~~

## Configuration

Copy the example environment file and provide the required credentials:

~~~bash
cp .env.example .env
~~~

~~~env
BOT_TOKEN=
API_ID=
API_HASH=
MONGO_URI=

GITHUB_APP_ID=
GITHUB_INSTALLATION_ID=
GITHUB_PRIVATE_KEY=

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_WEBHOOK_SECRET=

TOKEN_ENCRYPTION_KEY=
WEBHOOK_URL=
REDIS_URL=
LOG_CHAT_ID=
~~~

### Token encryption

<code>TOKEN_ENCRYPTION_KEY</code> is a Fernet key used to encrypt GitHub OAuth access and refresh tokens before MongoDB storage.

Generate one with:

~~~bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
~~~

Keep this key stable. If it changes, previously encrypted GitHub credentials cannot be decrypted.

## GitHub OAuth callback

Set the GitHub OAuth callback to:

~~~text
https://your-domain.example/oauth/callback
~~~

The value must correspond to <code>WEBHOOK_URL</code>:

~~~env
WEBHOOK_URL=https://your-domain.example
~~~

## Webhook endpoint

GitHub repository integrations send events to:

~~~text
POST /webhooks/github
~~~

The service also exposes:

~~~text
GET /health
GET /oauth/callback
~~~

The webhook endpoint validates the GitHub signature before accepting an event. Repository webhook creation is supported through GitHub’s repository hooks API. citeturn0search0

## Run locally

~~~bash
pip install -r requirements.txt
python -m Github
~~~

FastAPI listens on port <code>8000</code> by default and uses the deployment platform’s <code>PORT</code> when provided.

## Docker

~~~bash
docker build -t github-telegram .
docker run --env-file .env -p 8000:8000 github-telegram
~~~

## Production requirements

- GitHub App
- GitHub OAuth application
- MongoDB
- Redis
- Public HTTPS URL
- Telegram bot credentials
- Stable Fernet encryption key

Never commit <code>.env</code>, private keys or OAuth secrets.

## Security model

**GitHub App authentication** — application-level GitHub access and installation authentication.

**User OAuth** — acts on behalf of the connected GitHub user.

**Stored credentials** — OAuth access and refresh tokens are encrypted before MongoDB storage.

**Webhook verification** — GitHub webhook signatures are validated before processing.

**Temporary sessions** — editing and review state can live in Redis with automatic expiration.

## Current status

### Implemented

- Telegram GitHub control center
- GitHub OAuth + PKCE
- Encrypted OAuth token storage
- GitHub App installation authentication
- Repository browsing
- Branch browsing
- File browsing
- File editing
- Git object based commits
- Commit conflict protection
- Pull request management
- Pull request reviews
- Pull request merge / close / reopen
- Repository webhooks
- GitHub event notifications
- Telegram replies to issue / PR notifications
- Redis session support
- MongoDB persistence
- FastAPI health / OAuth / webhook service
- Docker deployment

### Pending

- GitHub Actions control center
- Workflow dispatch with inputs
- Workflow run monitoring
- Job logs and artifacts
- Issue management
- Reviewer assignment UI
- Multi-file commit staging
- Rich diff viewer
- Telegram WebApp code editor
- More webhook event controls
- Repository and account settings

## License

See the repository license for usage and distribution terms.

---

<div align="center">

**GitHub for Telegram**

Built around GitHub’s API, Telegram and a focused management workflow.

</div>
