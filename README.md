<div align="center">

# GitHub

**A focused GitHub control center built for Telegram.**

Manage repositories, source files, branches, commits, pull requests, reviews, integrations and notifications from a clean Telegram interface.

<p>
  <img src="https://i.ibb.co/WWS60dJP/tmp-otmadsf.jpg" alt="GitHub for Telegram" width="900">
</p>

<p>
  <a href="https://github.com/TheJinWooSung/Github">Repository</a>
  ·
  <a href="https://github.com/TheJinWooSung/Github/issues">Issues</a>
  ·
  <a href="https://github.com/TheJinWooSung/Github/pulls">Pull requests</a>
</p>

</div>

---

## Overview

GitHub for Telegram turns Telegram into a practical control surface for GitHub.

It combines a Kurigram bot, GitHub App authentication, GitHub OAuth, FastAPI webhooks, MongoDB and Redis. The bot talks directly to GitHub's API instead of maintaining a separate Git mirror.

The interface is designed around short actions and focused repository screens rather than a noisy dashboard.

## What it can do

| Area | Capabilities |
| --- | --- |
| Repository | Browse, search and open repository dashboards |
| Source | Browse branches, directories and files |
| Editing | Read, edit and review file changes |
| Commits | Build Git objects and create commits |
| Pull requests | Inspect files, commits and reviews |
| Reviews | Approve, request changes and comment |
| PR lifecycle | Merge, close, reopen and handle drafts |
| Integrations | Create and remove repository webhooks |
| Notifications | Receive GitHub repository events in Telegram |
| Linked repositories | Link, switch and remove repositories per Telegram user |
| Releases | Latest release, creation and generated changelogs |
| Search | Issues, pull requests and repository code search |
| Actions | Workflow dispatch with inputs, runs, reruns, cancellation and logs |
| Replies | Post supported GitHub comments from Telegram |
| Authentication | OAuth with PKCE and encrypted token storage |
| Sessions | Redis-backed temporary editing and review state |
| Web service | Health checks, OAuth callback and webhook receiver |

## Telegram workflow

The main flow is intentionally compact:

~~~text
/start
   ↓
Connect GitHub
   ↓
Repository browser
   ↓
Repository dashboard
   ├── Files
   ├── Commits
   ├── Branches
   ├── Pull requests
   ├── Issues
   ├── Actions
   ├── Releases
   ├── Contributors
   └── Deployments
~~~

### Commands

| Command | Purpose |
| --- | --- |
| `/connect` `/disconnect` `/me` | GitHub authentication |
| `/addrepo` `/removerepo` `/repos` `/repo` | Linked repository management |
| `/star` `/unstar` `/watch` `/unwatch` | Repository subscriptions |
| `/fork` `/archive` `/unarchive` `/default` | Repository state |
| `/contributors` `/languages` `/branches` `/branch` | Repository information |
| `/issue` `/comment` `/close` `/reopen` | Issue lifecycle |
| `/assign` `/assignme` `/unassign` `/label` `/labels` | Issue metadata |
| `/lock` `/unlock` `/pin` `/unpin` `/milestone` | Issue moderation |
| `/commit` `/commits` `/compare` | Commit history and comparisons |
| `/approve` `/requestchanges` `/merge` | Pull request review and merge |
| `/draft` `/ready` `/checks` `/files` `/diff` `/reviews` | Pull request inspection |
| `/request` `/pr` | Reviewer and pull request search |
| `/actions` `/run` `/rerun` `/cancel` `/logs` | GitHub Actions control |
| `/release` `/changelog` | Releases and release notes |
| `/find` `/search` | Issue and code search |
| `/stats` `/activity` `/settings` | Repository monitoring |
| `/mute` `/done` `/read` | Telegram notification state |
| `/newintegration` `/listintegrations` `/delintegration` | GitHub webhook integrations |
| `/privacy` `/help` | Privacy and command reference |

## Repository management

Each repository gets a focused dashboard for common GitHub operations.

### Source browsing

- Branches
- Tags
- Directories
- Files
- File contents
- Repository metadata
- Contributors
- Releases
- Deployments

### Editing and commits

Editing is session-based so content can be changed and reviewed before the final Git operation.

~~~text
Open file
   ↓
Edit content
   ↓
Review changes
   ↓
Commit message
   ↓
Confirm
   ↓
Create blobs / tree / commit
   ↓
Update branch reference
~~~

The commit engine checks the branch head before applying the final reference update, reducing the chance of silently overwriting newer work.

## Pull requests

Pull requests have a dedicated Telegram management flow.

| Action | Support |
| --- | :---: |
| View pull requests | ✓ |
| Inspect changed files | ✓ |
| Inspect commits | ✓ |
| View reviews | ✓ |
| Approve | ✓ |
| Request changes | ✓ |
| Review comment | ✓ |
| Merge | ✓ |
| Close / reopen | ✓ |
| Draft lifecycle | ✓ |

Where available, merge operations use the current pull-request head SHA so a stale Telegram screen does not blindly merge a changed branch.

## GitHub integrations

Repositories can be connected to Telegram notifications through GitHub webhooks.

~~~text
push
pull_request
issues
release
workflow_run
star
~~~

Webhook requests are authenticated with GitHub's `X-Hub-Signature-256` HMAC signature before processing.

Delivery IDs are persisted so duplicate webhook deliveries can be detected instead of repeatedly forwarding the same event.

## Reply from Telegram

Supported issue and pull-request notifications can be turned into GitHub comments directly from Telegram.

~~~text
GitHub event
     ↓
Telegram notification
     ↓
Reply
     ↓
GitHub issue / pull request comment
~~~

## Architecture

~~~text
                         ┌──────────────────────┐
                         │       Telegram       │
                         │   Bot + Inline UI    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       Kurigram       │
                         │       Handlers       │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
      │    GitHub    │      │    Redis     │      │   MongoDB    │
      │ REST / App   │      │   Sessions   │      │   Storage    │
      └──────┬───────┘      └──────────────┘      └──────────────┘
             │
             ▼
      ┌────────────────────┐
      │      FastAPI       │
      │ OAuth / Webhooks   │
      └────────────────────┘
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
│   ├── actions.py
│   ├── action_commands.py
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

## Authentication

The project separates application-level GitHub access from user-level authorization.

### GitHub App

Used for installation authentication and application-level GitHub operations.

### GitHub OAuth

Used when an action needs to operate on behalf of a connected GitHub user.

OAuth uses PKCE and the resulting credentials are encrypted before being stored.

## Configuration

Create the environment file:

~~~bash
cp .env.example .env
~~~

Required configuration:

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

Generate the Fernet encryption key:

~~~bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
~~~

Keep `TOKEN_ENCRYPTION_KEY` stable. Existing encrypted credentials cannot be decrypted after changing the key.

## Web service

The service exposes:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Health check |
| `GET /oauth/callback` | GitHub OAuth callback |
| `POST /webhooks/github` | GitHub webhook receiver |

Set the public base URL:

~~~env
WEBHOOK_URL=https://your-domain.example
~~~

The OAuth callback becomes:

~~~text
https://your-domain.example/oauth/callback
~~~

The webhook endpoint validates the GitHub signature before processing events.

## Run locally

~~~bash
git clone https://github.com/TheJinWooSung/Github.git
cd Github

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m Github
~~~

The FastAPI service uses port `8000` by default and respects the platform-provided `PORT` variable when available.

## Docker

~~~bash
docker build -t github-telegram .
docker run --env-file .env -p 8000:8000 github-telegram
~~~

For production, provide a public HTTPS endpoint, persistent MongoDB/Redis instances and securely managed GitHub and Telegram credentials.

## Security

- GitHub OAuth credentials are encrypted before MongoDB storage.
- OAuth authorization uses PKCE.
- GitHub webhook signatures are verified before processing.
- Temporary editing and review sessions expire automatically.
- GitHub App credentials stay outside the repository.
- Secrets belong in deployment environment variables, never in Git.
- Do not commit `.env`, private keys, OAuth secrets or encryption keys.

## Roadmap

### Core

- [x] Repository browser
- [x] Branch and file browser
- [x] File editing
- [x] Git object based commits
- [x] Pull request management
- [x] Pull request reviews
- [x] Repository webhooks
- [x] GitHub event notifications
- [x] Telegram issue / PR replies
- [x] MongoDB persistence
- [x] Redis sessions
- [x] FastAPI service
- [x] Docker deployment
- [x] GitHub Actions workflow browser
- [x] Workflow dispatch
- [x] Workflow run monitoring
- [x] Run cancellation and reruns
- [x] Workflow jobs and logs
- [x] Workflow artifacts
- [x] Workflow dispatch inputs through command arguments
- [x] Issue management commands
- [x] Reviewer assignment commands
- [x] Safe merge confirmation
- [x] Release and changelog commands
- [x] Repository linked-context management
- [x] Notification preferences
- [x] OAuth authorization revocation
- [x] Python compile CI

### Remaining product expansion

- [ ] Multi-file commit staging UI
- [ ] Telegram WebApp editor
- [ ] Rich interactive diff viewer
- [ ] GitHub Discussions UI and answer workflow
- [ ] Full webhook event management UI

## Development

The codebase keeps Telegram handlers, GitHub API operations, persistence, sessions and web endpoints separated so individual features can evolve without turning the bot into one large module.

Contributions should keep the same focus: production-ready behavior, compact Telegram UI and no unnecessary dependencies.

## License

See the repository license for the applicable terms.

---

<div align="center">

**GitHub for Telegram**

A focused GitHub management experience, built around Telegram.

</div>