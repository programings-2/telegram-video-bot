# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_formats_keyboard(formats_list):
    """
    formats_list: list of dicts with keys: short_id, label
    نُرجع InlineKeyboardMarkup
    """
    buttons = []
    for f in formats_list:
        # callback_data قصير مثل: "fmt:1" أو "audio"
        buttons.append([InlineKeyboardButton(f['label'], callback_data=f"fmt:{f['short_id']}")])

    # صف إضافي لاستخراج صوتي/معلومات/إعادة المحاولة
    buttons.append([
        InlineKeyboardButton("🎵 استخراج صوت (MP3)", callback_data="action:audio"),
        InlineKeyboardButton("ℹ️ معلومات", callback_data="action:info")
    ])
    buttons.append([
        InlineKeyboardButton("🔄 إعادة محاولة", callback_data="action:retry"),
        InlineKeyboardButton("🔙 إلغاء", callback_data="action:cancel")
    ])
    return InlineKeyboardMarkup(buttons)
