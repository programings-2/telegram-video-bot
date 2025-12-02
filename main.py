 # main.py 
 # main.py
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from utils import extract_url, ensure_downloads_dir
from downloader import MediaDownloader
from session import SessionManager
from keyboards import build_formats_keyboard
from captions import video_caption, audio_caption

# Logger
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ensure downloads folder
ensure_downloads_dir("downloads")

# instances
sessions = SessionManager(ttl_seconds=600)
downloader = MediaDownloader()


# -------------------------
# Handlers
# -------------------------
class BotHandlers:

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 أهلاً! أرسل رابط فيديو/صوت من أي موقع وسأجهّز لك الخيارات.\n"
            "🔰 يدعم المواقع التي تدعمها مكتبة yt-dlp."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "استخدم:\n"
            "• أرسل رابط الفيديو أو الصوت\n"
            "• اختر الجودة من الأزرار\n"
            "• أو اختر استخراج صوت MP3\n\n"
            "ملاحظة: إذا كان الملف كبيرًا جداً، قد لا يرسله التليجرام (حدود 2GB للمستخدمين العاديين)."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        # خزن الجلسة (نخزن map من short_id -> format_id)
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

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data  # مثال: "fmt:1" أو "action:audio"
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

            # إرسال الملف (بأمان مع فتح الملف داخل with)
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
                # حذف الملف مؤقتًا
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            await query.edit_message_text("✅ تم الإرسال. شكراً لاستخدام البوت!")
            # نمسح الجلسة بعد الإرسال
            sessions.clear(chat_id)
            return

        # إجراءات عامة
        if data == "action:audio":
            if not session:
                await query.edit_message_text("❌ انتهاء الجلسة. أعد إرسال الرابط.")
                return
            await query.edit_message_text("⏳ جاري استخراج الصوت (MP3)...")
            url = session.get("url")
            filepath, info = await downloader.download_extract_audio(url)
            if not filepath:
                await query.edit_message_text("❌ فشل استخراج الصوت.")
                return
            try:
                cap = audio_caption(info)
                with open(filepath, "rb") as f:
                    await context.bot.send_audio(query.message.chat.id, f, caption=cap)
            finally:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            await query.edit_message_text("✅ تم استخراج وإرسال الصوت!")
            sessions.clear(chat_id)
            return

        if data == "action:info":
            if not session:
                await query.edit_message_text("❌ انتهاء الجلسة.")
                return
            info = session.get("info", {})
            title = info.get("title", "بدون عنوان")
            duration = info.get("duration", 0)
            minutes = duration // 60
            seconds = duration % 60
            text = (
                f"ℹ️ *معلومات الفيديو*\n"
                f"• العنوان: {title}\n"
                f"• المدة: {minutes}:{seconds:02d}\n"
                f"• uploader: {info.get('uploader','غير معروف')}\n"
                f"• views: {info.get('view_count',0)}"
            )
            await query.edit_message_text(text, parse_mode="Markdown")
            return

        if data == "action:retry":
            # نعيد الطلب: نطلب من المستخدم إعادة إرسال الرابط
            sessions.clear(chat_id)
            await query.edit_message_text("🔁 تم إلغاء الجلسة. الرجاء إعادة إرسال الرابط.")
            return

        if data == "action:cancel":
            sessions.clear(chat_id)
            await query.edit_message_text("❌ تم الإلغاء.")
            return

        # أي callback غير معروف
        await query.edit_message_text("⚠️ أمر غير معروف.")

# -------------------------
# Main
# -------------------------
def main():
    # اقرأ التوكن من متغير البيئة — أو عدّله هنا مباشرة (لا تترك التوكن مكشوفاً في السجلات)
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise SystemExit("❌ ضع TELEGRAM_BOT_TOKEN في متغير البيئة قبل التشغيل.")

    app = Application.builder().token(TOKEN).build()
    handlers = BotHandlers()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.callback_query))

    print("🚀 Universal Bot is running...")
    app.run_polling(allowed_updates=None)

if __name__ == "__main__":
    main()
