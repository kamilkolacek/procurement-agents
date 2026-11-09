"""CLI: python -m spend_classification.synth [--seed N] [--out DIR --golden DIR]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spend_classification.synth.generate import DEFAULT_SEED, generate

AGENT_DIR = Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic spend data and answer key.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, help="exports dir (default: data/synthetic)")
    ap.add_argument("--golden", type=Path, help="answer key dir (default: evals/golden)")
    args = ap.parse_args(argv)
    m = generate(AGENT_DIR, args.seed, args.out, args.golden)
    print(json.dumps(m["counts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
