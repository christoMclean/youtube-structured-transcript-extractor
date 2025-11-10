from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp

LOG = logging.getLogger(__name__)

_YT_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})"
)

def parse_video_id(url: str) -> Optional[str]:
    """
    Extract a YouTube video id from common URL patterns.
    """
    m = _YT_URL_RE.search(url)
    return m.group(1) if m else None

class YouTubeClient:
    """
    Thin wrapper around youtube-transcript-api and yt-dlp for metadata.
    """

    def __init__(self) -> None:
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }

    def video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Returns a normalized metadata dict. Fails gracefully.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            # Normalize some fields
            upload_date_iso = None
            if "upload_date" in info and info["upload_date"]:
                # upload_date like "20240131"
                s = str(info["upload_date"])
                try:
                    upload_date_iso = datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%dT00:00:00Z")
                except Exception:  # noqa: BLE001
                    upload_date_iso = None
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "channel_id": info.get("channel_id"),
                "duration": info.get("duration"),
                "upload_date_iso": upload_date_iso,
                "thumbnail": info.get("thumbnail"),
            }
        except Exception as e:  # noqa: BLE001
            LOG.warning("yt-dlp metadata fetch failed for %s: %s", video_id, e)
            return {}

    def fetch_captions(
        self, video_id: str, preferred_lang: Optional[str] = None
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[bool]]:
        """
        Returns (segments, language, has_auto_captions).
        Each segment: {"start": float_seconds, "end": float_seconds, "text": str}
        """
        try:
            # get_transcript prefers a language; list_transcripts for more control
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            lang = None
            auto = None

            if preferred_lang:
                # Try exact language first
                try:
                    transcript = transcripts.find_manually_created_transcript([preferred_lang])
                    lang = transcript.language_code
                    auto = False
                except Exception:
                    try:
                        transcript = transcripts.find_generated_transcript([preferred_lang])
                        lang = transcript.language_code
                        auto = True
                    except Exception:
                        transcript = None

            if transcript is None:
                # Fall back to any manually created transcript
                try:
                    transcript = next(t for t in transcripts if not t.is_generated)
                    lang = transcript.language_code
                    auto = False
                except StopIteration:
                    # Fall back to first generated
                    transcript = next(iter(transcripts))
                    lang = transcript.language_code
                    auto = transcript.is_generated

            raw = transcript.fetch()
            # Normalize to {start,end,text}
            segments: List[Dict[str, Any]] = []
            for r in raw:
                start = float(r.get("start", 0.0))
                dur = float(r.get("duration", 0.0))
                end = start + dur
                segments.append({"start": round(start, 2), "end": round(end, 2), "text": r.get("text", "")})
            return segments, lang, auto
        except (TranscriptsDisabled, NoTranscriptFound):
            raise
        except Exception as e:  # noqa: BLE001
            LOG.error("Unexpected caption fetch error for %s: %s", video_id, e)
            raise