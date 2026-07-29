import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
LOG_URL = os.getenv("LOG_URL")

client = OpenAI(
    base_url="https://aipipe.org/openai/v1",
    api_key=AIPIPE_TOKEN,
)

LOG_FILE = "run.jsonl"

conversation_history = {}


def log_event(event):
    event["timestamp"] = time.time()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    user_text = update.message.text

    log_event({
        "type": "incoming",
        "chat_id": chat_id,
        "text": user_text
    })

    history = conversation_history.setdefault(chat_id, [])

    history.append({
        "role": "user",
        "content": user_text
    })

    system_prompt = """
You are a careful data analyst.

Always answer ONLY the LAST user message.

Return ONLY valid JSON.

No markdown.

No explanation.

No code block.

If the requested JSON contains a field called log_url, populate it with the value provided by the application.
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            }
        ] + history[-6:]
    )

    reply = response.choices[0].message.content.strip()

    history.append({
        "role": "assistant",
        "content": reply
    })

    try:
        obj = json.loads(reply)

    except Exception:

        start = reply.find("{")
        end = reply.rfind("}")

        obj = json.loads(reply[start:end + 1])

    if isinstance(obj, dict) and "log_url" in obj:
        obj["log_url"] = LOG_URL

    final_reply = json.dumps(obj)

    log_event({
        "type": "outgoing",
        "chat_id": chat_id,
        "text": final_reply
    })

    await update.message.reply_text(final_reply)


app = ApplicationBuilder().token(
    TELEGRAM_BOT_TOKEN
).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot is running...")

app.run_polling()