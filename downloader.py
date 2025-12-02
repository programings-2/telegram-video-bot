# downloader.py
import yt_dlp
import asyncio
import os
import uuid
from utils import safe_filename, ensure_downloads_dir

DOWNLOAD_DIR = ensure_downloads_dir("downloads")

COMMON_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extractor_args": {
        "tiktok": {"api_hostname": "api22-normal-c-useast2a.tiktokv.com"},
    },
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    },
    "socket_timeout": 30,
    "retries": 3,
    "geo_bypass": True,
    "nocheckcertificate": True,
}

class MediaDownloader:
    def __init__(self):
        pass

    async def get_info(self, url: str):
        def run():
            opts = {**COMMON_OPTS}
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        try:
            return await asyncio.to_thread(run)
        except Exception as e:
            print(f"Error getting info: {e}")
            return None

    def _prepare_formats(self, info):
        fmts = info.get("formats", [])
        choices = []
        seen = set()
        idx = 1
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
        return choices

    async def list_formats(self, url: str):
        info = await self.get_info(url)
        if not info:
            return None, None
        choices = self._prepare_formats(info)
        return info, choices

    async def download_by_format(self, url: str, format_id: str):
        file_id = uuid.uuid4().hex
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

        ydl_opts = {
            **COMMON_OPTS,
            "format": format_id,
            "outtmpl": outtmpl,
            "noplaylist": True,
        }

        def run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, info

        try:
            return await asyncio.to_thread(run)
        except Exception as e:
            print(f"Error downloading: {e}")
            return None, None

    async def download_extract_audio(self, url: str):
        file_id = uuid.uuid4().hex
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

        ydl_opts = {
            **COMMON_OPTS,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        def run():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not filename.lower().endswith(".mp3"):
                    base = os.path.splitext(filename)[0]
                    filename = base + ".mp3"
                return filename, info

        try:
            return await asyncio.to_thread(run)
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return None, None
