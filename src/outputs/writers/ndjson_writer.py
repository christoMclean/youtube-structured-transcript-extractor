from __future__ import annotations

import json
from typing import Dict, Any, Iterable

def write_ndjson_file(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")