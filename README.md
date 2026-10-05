# GitHub for Telegram

A Telegram GitHub control center built around GitHub App authentication, user OAuth, MongoDB, Redis and FastAPI.

## Commands

- /start
- /connect
- /repos
- /newintegration owner/repository
- /listintegrations
- /delintegration repository_id

## OAuth

/ connect opens the GitHub authorization flow with PKCE. The callback is served at:

`WEBHOOK_URL/oauth/callback`

User access tokens are encrypted before being stored in MongoDB.

## Run

```bash
python -m Github
```

The process runs the Telegram bot and FastAPI server together. Set `PORT` when the deployment platform provides one.

## Required configuration

Configure `.env.example` in the deployment environment.

Generate a Fernet key for `TOKEN_ENCRYPTION_KEY` and keep it stable. Changing it makes previously stored GitHub tokens unreadable.

The GitHub App callback URL must exactly match `WEBHOOK_URL/oauth/callback`.
