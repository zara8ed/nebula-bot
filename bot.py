import asyncio
import logging
import os

from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nebula-bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

TELEGRAM_ALLOWED = {u.strip() for u in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()}
DISCORD_ALLOWED = {u.strip() for u in os.environ.get("DISCORD_ALLOWED_USERS", "").split(",") if u.strip()}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "You are a helpful assistant.")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
HISTORY_LIMIT = int(os.environ.get("HISTORY_LIMIT", "10"))

if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY is not set; bot will fail when asked to reply.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY or "missing", base_url=OPENAI_BASE_URL)
history: dict[int, list[dict]] = {}


def tel_allowed(uid: str | int) -> bool:
    return not TELEGRAM_ALLOWED or str(uid) in TELEGRAM_ALLOWED


def dc_allowed(uid: str | int) -> bool:
    return not DISCORD_ALLOWED or str(uid) in DISCORD_ALLOWED


def add_history(chat_id: int, role: str, content: str) -> list[dict]:
    msgs = history.get(chat_id, [])
    msgs.append({"role": role, "content": content})
    msgs = msgs[-(HISTORY_LIMIT * 2):]
    history[chat_id] = msgs
    return msgs


async def ask_llm(chat_id: int, user_text: str) -> str:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + add_history(chat_id, "user", user_text)
    try:
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=msgs,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        answer = resp.choices[0].message.content or ""
    except Exception as exc:
        log.exception("LLM call failed")
        return f"Error: {exc}"
    add_history(chat_id, "assistant", answer)
    return answer


async def telegram_server():
    if not TELEGRAM_TOKEN:
        log.info("Telegram disabled (no TELEGRAM_BOT_TOKEN)")
        return

    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message
        if not msg or not msg.text:
            return
        if not tel_allowed(msg.from_user.id):
            await msg.reply_text("Access denied.")
            return
        if msg.text.lower() in ("/start", "/help"):
            await msg.reply_text("Hello! Send me any message and I will reply using the configured LLM.")
            return
        answer = await ask_llm(msg.chat_id, msg.text)
        await msg.reply_text(answer)

    async def on_reset(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        history.pop(update.message.chat_id, None)
        await update.message.reply_text("Conversation history cleared.")

    app.add_handler(CommandHandler("reset", on_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("Telegram bot started")
    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()
        await app.shutdown()


async def discord_server():
    if not DISCORD_TOKEN:
        log.info("Discord disabled (no DISCORD_BOT_TOKEN)")
        return

    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        log.info("Discord bot started as %s", client.user)

    @client.event
    async def on_message(message):
        if message.author == client.user or message.author.bot:
            return
        if not dc_allowed(message.author.id):
            await message.channel.send("Access denied.")
            return
        if isinstance(message.channel, discord.DMChannel) or client.user in message.mentions:
            text = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()
            if not text:
                return
            if text.lower() == "!reset":
                history.pop(message.channel.id, None)
                await message.channel.send("Conversation history cleared.")
                return
            async with message.channel.typing():
                answer = await ask_llm(message.channel.id, text)
            await message.channel.send(answer)

    try:
        await client.start(DISCORD_TOKEN)
    finally:
        await client.close()


async def keep_alive():
    while True:
        await asyncio.sleep(3600)


async def main():
    tasks = [asyncio.create_task(t) for t in (telegram_server(), discord_server(), keep_alive())]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())