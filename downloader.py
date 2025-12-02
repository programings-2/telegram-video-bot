# downloader.py
import os
import asyncio
from yt_dlp import YoutubeDL
from pathlib import Path
from utils import ensure_downloads_dir, safe_filename

DOWNLOADS_DIR = ensure_downloads_dir("downloads")

class MediaDownloader:
    def __init__(self, cookies_file=None):
        """
        cookies_file: مسار ملف cookies بصيغة Netscape (مثلاً exported من المتصفح)
        """
        self.cookies_file = cookies_file

    async def list_formats(self, url):
        """قائمة الصيغ المتاحة للفيديو"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_list_formats, url)

    def _sync_list_formats(self, url):
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "cookiefile": self.cookies_file,
            "force_generic_extractor": False,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = []
                for i, f in enumerate(info.get("formats", []), start=1):
                    label = f"{f.get('format_note','')} {f.get('ext','')}"
                    formats.append({
                        "short_id": str(i),
                        "format_id": f["format_id"],
                        "label": label
                    })
                return info, formats
        except Exception as e:
            print("⚠️ خطأ في استخراج الصيغ:", e)
            return None, None

    async def download_by_format(self, url, format_id):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_download_by_format, url, format_id)

    def _sync_download_by_format(self, url, format_id):
        filename = safe_filename(url.split("/")[-1])
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        ydl_opts = {
            "format": format_id,
            "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
            "cookiefile": self.cookies_file,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                final_path = ydl.prepare_filename(info)
            return final_path, info
        except Exception as e:
            print("⚠️ خطأ في التحميل:", e)
            return None, None

    async def download_extract_audio(self, url):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_download_extract_audio, url)

    def _sync_download_extract_audio(self, url):
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
            "extractaudio": True,
            "audioformat": "mp3",
            "cookiefile": self.cookies_file,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                final_path = ydl.prepare_filename(info)
            return final_path, info
        except Exception as e:
            print("⚠️ خطأ في استخراج الصوت:", e)
            return None, None
