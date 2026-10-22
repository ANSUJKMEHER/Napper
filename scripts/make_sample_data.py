#!/usr/bin/env python3
"""Generate the demo CSVs into inbox/. Run: python scripts/make_sample_data.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from napper.sample_data import generate_all  # noqa: E402

if __name__ == "__main__":
    counts = generate_all()
    for k, v in counts.items():
        print(f"{k}: {v} rows")
