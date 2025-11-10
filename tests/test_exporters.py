import json
import os
import sys
import tempfile

# Allow running tests directly from repo root
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from outputs.exporters import ExportCoordinator

ROWS = [
    {
        "videoId": "vid1",
        "videoUrl": "https://www.youtube.com/watch?v=vid1",
        "title": "T1",
        "channelId": "C1",
        "channelName": "Ch1",
        "language": "en",
        "hasAutoCaptions": False,
        "captionFormat": "array_with_timestamps",
        "captions": [{"start": 0.0, "end": 1.0, "text": "Hi"}],
        "duration": 60.0,
        "publishedAt": "2024-01-01T00:00:00Z",
        "thumbnailUrl": "http://i.ytimg.com/vi/vid1/hqdefault.jpg",
        "requestedFormat": "array_with_timestamps",
        "error": None,
        "createdAt": "2025-11-10T00:00:00Z",
    }
]

def test_export_json_csv_ndjson():
    with tempfile.TemporaryDirectory() as td:
        ec = ExportCoordinator(outdir=td, basename="test")
        p_json = ec.write_json(ROWS)
        p_csv = ec.write_csv(ROWS)
        p_nd = ec.write_ndjson(ROWS)

        assert os.path.exists(p_json)
        assert os.path.exists(p_csv)
        assert os.path.exists(p_nd)

        data = json.load(open(p_json, "r", encoding="utf-8"))
        assert isinstance(data, list) and data[0]["videoId"] == "vid1"

        # CSV header check
        with open(p_csv, "r", encoding="utf-8") as f:
            header = f.readline().strip()
        assert "videoId,videoUrl,title" in header

        # NDJSON line
        with open(p_nd, "r", encoding="utf-8") as f:
            line = f.readline()
        rec = json.loads(line)
        assert rec["videoId"] == "vid1"