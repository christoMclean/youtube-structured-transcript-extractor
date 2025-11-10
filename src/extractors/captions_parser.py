from __future__ import annotations

from typing import List, Dict, Any

class CaptionFormat:
    ARRAY = "array"
    ARRAY_TS = "array_with_timestamps"
    XML = "xml"
    XML_TS = "xml_with_timestamps"
    ONE_LINE = "one_line_text"

def parse_captions_payload(segments: List[Dict[str, Any]], fmt: str):
    """
    Convert normalized caption segments into the requested payload.
    - array: ["text", ...]
    - array_with_timestamps: [{"start": float, "end": float, "text": str}, ...]
    """
    if fmt == CaptionFormat.ARRAY:
        return [s.get("text", "") for s in segments]
    elif fmt == CaptionFormat.ARRAY_TS:
        # Ensure only the needed keys and correct types
        out = []
        for s in segments:
            out.append({"start": float(s["start"]), "end": float(s["end"]), "text": str(s["text"])})
        return out
    elif fmt in (CaptionFormat.XML, CaptionFormat.XML_TS, CaptionFormat.ONE_LINE):
        # Those are assembled elsewhere (xml_formatter / one_line_text)
        # Here we just return the raw to allow downstream formatters to handle
        return segments
    else:
        raise ValueError(f"Unsupported caption format: {fmt}")

def one_line_text(segments: List[Dict[str, Any]]) -> str:
    """
    Joins all texts into a single line with spaces, removing internal newlines.
    """
    tokens = []
    for s in segments:
        t = (s.get("text") or "").replace("\n", " ").strip()
        if t:
            tokens.append(t)
    return " ".join(tokens)