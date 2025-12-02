# captions.py
def video_caption(info, quality_label):
    title = info.get("title", "بدون عنوان")
    duration = info.get("duration", 0)
    mins = duration // 60
    secs = duration % 60
    return (
        f"🎬 {title}\n"
        f"⏱️ {mins}:{secs:02d}\n"
        f"🔰 الجودة: {quality_label}"
    )

def audio_caption(info):
    title = info.get("title", "بدون عنوان")
    duration = info.get("duration", 0)
    mins = duration // 60
    secs = duration % 60
    return f"🎵 {title}\n⏱️ {mins}:{secs:02d}\n⚡ تم استخراج الصوت MP3"
