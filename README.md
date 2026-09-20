# Nebula Bot

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/YOUR_TEMPLATE_ID)

A minimal Telegram/Discord chat bot. It receives your messages, sends them to an OpenAI-compatible LLM endpoint (Groq by default), and replies. It only talks to text endpoints - nothing else is installed.

## Env vars

| Var | Required | Default |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | at least one of TG/Discord | - |
| `DISCORD_BOT_TOKEN` | at least one of TG/Discord | - |
| `OPENAI_API_KEY` | yes | - |
| `OPENAI_BASE_URL` | no | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | no | `llama-3.3-70b-versatile` |
| `SYSTEM_PROMPT` | no | `You are a helpful assistant.` |
| `TELEGRAM_ALLOWED_USERS` | no | empty = allow all |
| `DISCORD_ALLOWED_USERS` | no | empty = allow all |
| `MAX_TOKENS` | no | `2048` |
| `TEMPERATURE` | no | `0.7` |
| `HISTORY_LIMIT` | no | `10` |

## Railway deploy

1. Create a Railway project from this repo (or `railway up`).
2. Set the env vars above. Telegram and Discord both run in one container; set only the token(s) you use.
3. Deploy. No volume needed.

## Local run

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export OPENAI_API_KEY=...
python bot.py
```

Commands:
- Telegram: `/reset` clears the conversation.
- Discord: `!reset` clears the conversation; in servers the bot only replies when mentioned.