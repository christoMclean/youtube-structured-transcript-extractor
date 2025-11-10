from __future__ import annotations

import csv
from typing import List, Dict, Any

def write_csv_file(path: str, rows: List[Dict[str, Any]]) -> None:
    # Determine columns from union of keys, ordered by first row
    if rows:
        fieldnames = list(rows[0].keys())
        # Include any extra keys appearing later
        for r in rows[1:]:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
    else:
        fieldnames = []

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in fieldnames})