from __future__ import annotations

import csv
import json
import os
from typing import List, Dict, Any

from .writers.json_writer import write_json_file
from .writers.csv_writer import write_csv_file
from .writers.ndjson_writer import write_ndjson_file

class ExportCoordinator:
    """
    Coordinates multiple writers and normalizes row structure for CSV/NDJSON.
    """

    def __init__(self, *, outdir: str, basename: str) -> None:
        self.outdir = outdir
        self.basename = basename
        os.makedirs(self.outdir, exist_ok=True)

    def write_json(self, rows: List[Dict[str, Any]]) -> str:
        path = os.path.join(self.outdir, f"{self.basename}.json")
        write_json_file(path, rows)
        return path

    def write_ndjson(self, rows: List[Dict[str, Any]]) -> str:
        path = os.path.join(self.outdir, f"{self.basename}.ndjson")
        write_ndjson_file(path, rows)
        return path

    def write_csv(self, rows: List[Dict[str, Any]]) -> str:
        """
        Flattens the rows for CSV; complex fields become JSON strings.
        """
        path = os.path.join(self.outdir, f"{self.basename}.csv")
        if not rows:
            # still write header with common fields
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "videoId",
                        "videoUrl",
                        "title",
                        "channelId",
                        "channelName",
                        "language",
                        "hasAutoCaptions",
                        "captionFormat",
                        "captions",
                        "duration",
                        "publishedAt",
                        "thumbnailUrl",
                        "requestedFormat",
                        "error",
                        "createdAt",
                    ]
                )
            return path

        norm_rows: List[Dict[str, Any]] = []
        for r in rows:
            # stringify captions (which could be array/object/XML)
            captions = r.get("captions")
            if isinstance(captions, (dict, list)):
                captions = json.dumps(captions, ensure_ascii=False)
            norm = dict(r)
            norm["captions"] = captions
            norm_rows.append(norm)

        write_csv_file(path, norm_rows)
        return path