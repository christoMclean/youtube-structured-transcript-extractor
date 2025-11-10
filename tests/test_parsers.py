import os
import sys

# Allow running tests directly from repo root
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from extractors.captions_parser import parse_captions_payload, CaptionFormat, one_line_text
from extractors.xml_formatter import captions_to_xml

SAMPLE = [
    {"start": 0.0, "end": 1.5, "text": "Hello"},
    {"start": 1.5, "end": 3.0, "text": "world!"},
    {"start": 3.0, "end": 4.0, "text": "New\nline"},
]

def test_array_format():
    out = parse_captions_payload(SAMPLE, CaptionFormat.ARRAY)
    assert out == ["Hello", "world!", "New\nline"]

def test_array_ts_format():
    out = parse_captions_payload(SAMPLE, CaptionFormat.ARRAY_TS)
    assert out[0]["start"] == 0.0 and out[1]["end"] == 3.0
    assert out[2]["text"] == "New\nline"

def test_one_line_text():
    out = one_line_text(SAMPLE)
    assert out == "Hello world! New line"

def test_xml_without_ts():
    xml = captions_to_xml(SAMPLE, with_timestamps=False)
    assert "<captions>" in xml and "</captions>" in xml
    assert "<c>Hello</c>" in xml

def test_xml_with_ts():
    xml = captions_to_xml(SAMPLE, with_timestamps=True)
    assert 'start="0.00"' in xml and 'end="1.50"' in xml