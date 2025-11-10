from __future__ import annotations

import html
from typing import List, Dict, Any

def captions_to_xml(segments: List[Dict[str, Any]], *, with_timestamps: bool) -> str:
    """
    Minimal XML (not TTML/WebVTT) that captures the text and optional timing.
    """
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<captions>"]
    for s in segments:
        text = html.escape(str(s.get("text", "")))
        if with_timestamps:
            parts.append(
                f'  <c start="{float(s.get("start", 0.0)):.2f}" end="{float(s.get("end", 0.0)):.2f}">{text}</c>'
            )
        else:
            parts.append(f"  <c>{text}</c>")
    parts.append("</captions>")
    return "\n".join(parts)