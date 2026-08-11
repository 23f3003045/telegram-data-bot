import json,os,re,time
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder,MessageHandler,ContextTypes,filters

load_dotenv()
BOT=os.environ["TELEGRAM_BOT_TOKEN"]
API=os.environ["AIPIPE_TOKEN"]
LOG_URL=os.environ["LOG_URL"]
client = OpenAI(
    base_url="https://aipipe.org/openai/v1",
    api_key=API,
    timeout=60,
)
LOG_FILE="run.jsonl"
history={}
def log(e):
    e["timestamp"]=time.time()
    with open(LOG_FILE,"a",encoding="utf-8") as f:f.write(json.dumps(e,ensure_ascii=False)+"\n")
def extract(t):
    try:return json.loads(t)
    except:pass
    m=re.search(r'\{.*\}',t,re.S)
    if not m:raise ValueError("No JSON")
    return json.loads(m.group())
async def handle(update:Update,context:ContextTypes.DEFAULT_TYPE):
    cid=update.effective_chat.id
    txt=update.message.text
    log({"type":"incoming","chat_id":cid,"text":txt})
    h=history.setdefault(cid,[])
    h.append({"role":"user","content":txt});h=h[-10:];history[cid]=h
    sys=('You are a careful data analyst. Answer ONLY the LAST user message. '
    'Return exactly one valid JSON object. Never use markdown, explanations or code fences. '
    'Follow the requested JSON schema exactly. Do not invent extra keys. '
    'If the schema includes log_url leave it empty.')
    try:
        r=client.chat.completions.create(model="gpt-5-mini",messages=[{"role":"system","content":sys}]+h)
        out=r.choices[0].message.content.strip()
        h.append({"role":"assistant","content":out})
        obj=extract(out)
        if isinstance(obj,dict) and "log_url" in obj: obj["log_url"]=LOG_URL
        final=json.dumps(obj,ensure_ascii=False)
    except Exception as e:
        print("AIPIPE ERROR:", repr(e))

    final = json.dumps({
        "error": "temporary_failure",
        "details": type(e).__name__
    })
 
    log({"type":"outgoing","chat_id":cid,"text":final})
    await update.message.reply_text(final)
async def err(update,context): print(context.error)
app=ApplicationBuilder().token(BOT).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle))
app.add_error_handler(err)
print("Bot is running...")
app.run_polling()
