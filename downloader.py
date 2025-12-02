# downloader.py
import yt_dlp
import asyncio
import os
import uuid
from utils import safe_filename, ensure_downloads_dir

DOWNLOAD_DIR = ensure_downloads_dir("downloads")

class MediaDownloader:
    def __init__(self):
        pass

    async def get_info(self, url: str):
        """تشغيل yt-dlp في thread لاستخراج المعلومات فقط"""
        def run():
            opts = {"quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        try:
            return await asyncio.to_thread(run)
        except Exception as e:
            return None

    def _prepare_formats(self, info):
        """
        من info نستخلص قائمة جودات مفهومة ونولد short_id لكل خيار
        نرجع قائمة من dicts: [{'short_id': '1','label':'1080p (mp4)','format_id': '249'} ...]
        """
        fmts = info.get("formats", [])
        choices = []
        seen = set()
        idx = 1
        # نفضّل الجودات التي تحتوي video/audio والملفات الأكبر حجماً أولًا
        # نَمر على الفورمات ونختار التي لديها filesize أو height
        for f in sorted(fmts, key=lambda x: (x.get("height") or 0, x.get("filesize") or 0), reverse=True):
            fmt_id = str(f.get("format_id") or f.get("format"))
            ext = f.get("ext", "")
            height = f.get("height")
            note = f.get("format_note") or (f"{height}p" if height else "")
            label = f"{note} ({ext})" if note else f"{ext}"
            key = (fmt_id, label)
            if key in seen:
                continue
            seen.add(key)
            short_id = str(idx)
            choices.append({
                "short_id": short_id,
                "label": label or fmt_id,
                "format_id": fmt_id,
                "ext": ext
            })
            idx += 1
            if idx > 20:
                break
        # أضف خيار صوتي عام إن وُجد
        # لكن عادة سيكون موجود كفورمات
        return choices

    async def list_formats(self, url: str):
        info = await self.get_info(url)
        if not info:
            return None, None
        choices = self._prepare_formats(info)
        return info, choices

    async def download_by_format(self, url: str, format_id: str):
        """
        ينزل باستخدام format_id المعطى (مثال: 'bestvideo[height<=720]+bestaudio/best' أو '140')
        يعيد (filepath, info) أو (None, None)
        """
        file_id = uuid.uuid4().hex
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

        ydl_opts = {
            "format": format_id,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            # يمكنك إضافة postprocessors هنا إذا أردت
        }

        def run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, info

        try:
            return await asyncio.to_thread(run)
        except Exception as e:
            return None, None

    async def download_extract_audio(self, url: str):
        """تنزيل واستخراج صوت MP3 باستخدام postprocessor"""
        file_id = uuid.uuid4().hex
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        def run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # بعد postprocessor اسم الملف سينتهي بـ .mp3 عادة
                filename = ydl.prepare_filename(info)
                # حاول تبديل الامتداد إلى mp3 إن لم يتغير
                if not filename.lower().endswith(".mp3"):
                    base = os.path.splitext(filename)[0]
                    filename = base + ".mp3"
                return filename, info

        try:
            return await asyncio.to_thread(run)
        except Exception:
            return None, None
