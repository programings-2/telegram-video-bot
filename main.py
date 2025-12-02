 import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, Dispatcher, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from utils import extract_url, ensure_downloads_dir
from downloader import MediaDownloader
from session import SessionManager
from keyboards import build_formats_keyboard
from captions import video_caption, audio_caption

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ensure_downloads_dir("downloads")

sessions = SessionManager(ttl_seconds=600)
downloader = MediaDownloader()

app = FastAPI()

# اقرأ التوكن من متغير البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("❌ ضع TELEGRAM_BOT_TOKEN في متغير البيئة قبل التشغيل.")

application = Application.builder().token(TOKEN).build()
dispatcher = application.dispatcher

# -------------------------
# Handlers
# -------------------------
class BotHandlers:

    async def start(self, update, context):
        await update.message.reply_text(
            "👋 أهلاً! أرسل رابط فيديو/صوت من أي موقع وسأجهّز لك الخيارات.\n"
            "🔰 يدعم المواقع التي تدعمها مكتبة yt-dlp."
        )

    async def help(self, update, context):
        await update.message.reply_text(
            "استخدم:\n"
            "• أرسل رابط الفيديو أو الصوت\n"
            "• اختر الجودة من الأزرار\n"
            "• أو اختر استخراج صوت MP3\n\n"
            "ملاحظة: إذا كان الملف كبيرًا جداً، قد لا يرسله التليجرام (حدود 2GB)."
        )

    async def handle_message(self, update, context):
        text = update.message.text or ""
        url = extract_url(text)
        if not url:
            await update.message.reply_text("❌ لم أجد رابط في رسالتك. أرسل رابط واضح.")
            return

        msg = await update.message.reply_text("🔍 جاري تحليل الرابط — الرجاء الانتظار...")

        info, formats = await downloader.list_formats(url)
        if not info or not formats:
            await msg.edit_text("❌ لم أستطع استخراج الصيغ من الرابط. ربما الموقع محمي أو الرابط غير صحيح.")
            return

        formats_map = {f['short_id']: f['format_id'] for f in formats}
        sessions.create(update.effective_chat.id, {
            "url": url,
            "info": info,
            "formats": formats_map,
            "formats_meta": {f['short_id']: f for f in formats}
        })

        kb = build_formats_keyboard([{"short_id": f['short_id'], "label": f['label']} for f in formats])
        title = info.get("title", "بدون عنوان")
        await msg.edit_text(f"🎬 *{title}*\n\nاختر الجودة من الأزرار أدناه:", parse_mode="Markdown", reply_markup=kb)

    async def callback_query(self, update, context):
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = query.message.chat.id
        session = sessions.get(chat_id)

        if data.startswith("fmt:"):
            short_id = data.split(":", 1)[1]
            if not session:
                await query.edit_message_text("❌ انتهت صلاحية الجلسة. أعد إرسال الرابط.")
                return
            fmt_map = session.get("formats", {})
            format_id = fmt_map.get(short_id)
            if not format_id:
                await query.edit_message_text("❌ خيار غير معروف. أعد إرسال الرابط.")
                return

            await query.edit_message_text("⏳ جاري التحميل — أعمل على تنزيل الملف الآن...")
            url = session.get("url")
            filepath, info = await downloader.download_by_format(url, format_id)
            if not filepath:
                await query.edit_message_text("❌ فشل التحميل. جرب جودة أخرى.")
                return

            try:
                ext = os.path.splitext(filepath)[1].lower()
                if ext in [".mp3", ".m4a", ".wav"]:
                    cap = audio_caption(info)
                    with open(filepath, "rb") as f:
                        await context.bot.send_audio(chat_id, f, caption=cap)
                else:
                    cap = video_caption(info, session["formats_meta"][short_id]["label"])
                    with open(filepath, "rb") as f:
                        await context.bot.send_video(chat_id, f, caption=cap)
            finally:
                try: os.remove(filepath)
                except: pass

            await query.edit_message_text("✅ تم الإرسال. شكراً لاستخدام البوت!")
            sessions.clear(chat_id)
            return

# -------------------------
# إضافة Handlers
# -------------------------
handlers = BotHandlers()
dispatcher.add_handler(CommandHandler("start", handlers.start))
dispatcher.add_handler(CommandHandler("help", handlers.help))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
dispatcher.add_handler(CallbackQueryHandler(handlers.callback_query))

# -------------------------
# Webhook endpoint لـ Render
# -------------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await dispatcher.process_update(update)
    return {"ok": True}

# Endpoint للتاكد ان السيرفر شغال
@app.get("/")
async def root():
    return {"status": "Bot is running"}
