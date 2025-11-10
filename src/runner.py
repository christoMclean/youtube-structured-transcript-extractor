import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Local imports
try:
    from extractors.youtube_client import YouTubeClient, parse_video_id
    from extractors.captions_parser import (
        CaptionFormat,
        parse_captions_payload,
        one_line_text,
    )
    from extractors.xml_formatter import captions_to_xml
    from outputs.exporters import ExportCoordinator
except ImportError:
    # Support running via `python src/runner.py` from repo root
    sys.path.append(os.path.dirname(__file__))
    from extractors.youtube_client import YouTubeClient, parse_video_id
    from extractors.captions_parser import (
        CaptionFormat,
        parse_captions_payload,
        one_line_text,
    )
    from extractors.xml_formatter import captions_to_xml
    from outputs.exporters import ExportCoordinator

LOG = logging.getLogger("runner")

def load_urls(urls_or_path: List[str]) -> List[str]:
    """
    Accepts list of URLs or a single file path. If a path is given and exists,
    load line-separated URLs from it.
    """
    if len(urls_or_path) == 1 and os.path.exists(urls_or_path[0]):
        path = urls_or_path[0]
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines()]
        return [ln for ln in lines if ln]
    # Otherwise treat them as URLs
    return urls_or_path

def build_item_schema(
    *,
    video_id: str,
    video_url: str,
    meta: Dict[str, Any],
    language: Optional[str],
    has_auto: Optional[bool],
    caption_format: str,
    captions_payload: Any,
    error: Optional[str],
) -> Dict[str, Any]:
    created_at = datetime.utcnow().isoformat() + "Z"
    return {
        "videoId": video_id,
        "videoUrl": video_url,
        "title": meta.get("title"),
        "channelId": meta.get("channel_id"),
        "channelName": meta.get("uploader"),
        "language": language,
        "hasAutoCaptions": has_auto,
        "captionFormat": caption_format,
        "captions": captions_payload if error is None else None,
        "duration": meta.get("duration"),
        "publishedAt": meta.get("upload_date_iso"),
        "thumbnailUrl": meta.get("thumbnail"),
        "requestedFormat": caption_format,
        "error": error,
        "createdAt": created_at,
    }

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract structured YouTube transcripts at scale."
    )
    p.add_argument(
        "inputs",
        nargs="+",
        help="One or more YouTube URLs or a single path to a text file with URLs (one per line).",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        default="array_with_timestamps",
        choices=[
            "array",
            "array_with_timestamps",
            "xml",
            "xml_with_timestamps",
            "one_line_text",
        ],
        help="Output caption format.",
    )
    p.add_argument(
        "--language",
        dest="language",
        default=None,
        help="Preferred language code (e.g., en). If not available, falls back to first available.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of concurrent fetches (used for batching, not threads).",
    )
    p.add_argument(
        "--out",
        dest="outdir",
        default="out",
        help="Output directory for exported files.",
    )
    p.add_argument(
        "--export",
        dest="export",
        default="json",
        choices=["json", "csv", "ndjson", "all"],
        help="Export format(s).",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    return p.parse_args()

def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    os.makedirs(args.outdir, exist_ok=True)

    urls = load_urls(args.inputs)
    if not urls:
        LOG.error("No input URLs found.")
        sys.exit(2)

    yt = YouTubeClient()
    results: List[Dict[str, Any]] = []

    # Simple batching to keep memory reasonable and allow progress
    batch_size = max(1, args.concurrency)
    caption_format = args.fmt

    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        LOG.info("Processing batch %d..%d / %d", i + 1, i + len(batch), len(urls))
        for url in batch:
            start_t = time.time()
            vid = parse_video_id(url)
            if not vid:
                LOG.warning("Unable to parse video id from URL: %s", url)
                item = build_item_schema(
                    video_id="",
                    video_url=url,
                    meta={},
                    language=None,
                    has_auto=None,
                    caption_format=caption_format,
                    captions_payload=None,
                    error="INVALID_URL",
                )
                results.append(item)
                continue

            try:
                meta = yt.video_metadata(vid)
            except Exception as e:  # noqa: BLE001
                LOG.exception("Metadata fetch failed for %s: %s", vid, e)
                meta = {}

            try:
                captions, lang, auto = yt.fetch_captions(vid, preferred_lang=args.language)
                LOG.debug("Fetched %d caption segments for %s", len(captions or []), vid)
                payload: Any
                if caption_format in (CaptionFormat.XML, CaptionFormat.XML_TS):
                    payload = captions_to_xml(captions or [], with_timestamps=(caption_format == CaptionFormat.XML_TS))
                elif caption_format == CaptionFormat.ONE_LINE:
                    payload = one_line_text(captions or [])
                else:
                    payload = parse_captions_payload(captions or [], caption_format)
                item = build_item_schema(
                    video_id=vid,
                    video_url=url,
                    meta=meta,
                    language=lang,
                    has_auto=auto,
                    caption_format=caption_format,
                    captions_payload=payload,
                    error=None,
                )
            except Exception as e:  # noqa: BLE001
                LOG.exception("Caption extraction failed for %s: %s", vid, e)
                item = build_item_schema(
                    video_id=vid,
                    video_url=url,
                    meta=meta,
                    language=None,
                    has_auto=None,
                    caption_format=caption_format,
                    captions_payload=None,
                    error=str(e),
                )
            finally:
                dur = time.time() - start_t
                LOG.info("Processed %s in %.2fs", vid or url, dur)
            results.append(item)

    # Export
    basename = f"youtube_transcripts_{int(time.time())}"
    export = ExportCoordinator(outdir=args.outdir, basename=basename)
    if args.export in ("json", "all"):
        export.write_json(results)
    if args.export in ("csv", "all"):
        export.write_csv(results)
    if args.export in ("ndjson", "all"):
        export.write_ndjson(results)

    # Also drop a compact JSON for quick inspection
    compact_path = os.path.join(args.outdir, f"{basename}_compact.json")
    with open(compact_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    LOG.info("Done. Wrote outputs to %s", os.path.abspath(args.outdir))

if __name__ == "__main__":
    main()