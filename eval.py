#!/usr/bin/env python3
"""Evaluate the PII redactor on a small synthetic labeled dataset.

Dataset format (JSONL): {"text": str, "entities": [[value, type], ...]}
Spans are located with str.find in entity order. A prediction counts as
correct only when span AND type match exactly.

Usage:
    python eval.py                  # uses eval_data.jsonl
    python eval.py --data other.jsonl --use-spacy
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from redact import detect


def load_gold(path: str) -> list[tuple[str, set[tuple[int, int, str]]]]:
    """Return [(text, {(start, end, type), ...}), ...]."""
    items = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = rec["text"]
            gold: set[tuple[int, int, str]] = set()
            pos = 0
            for value, etype in rec["entities"]:
                idx = text.find(value, pos)
                if idx == -1:
                    raise ValueError(f"{path}:{lineno}: entity {value!r} not found in text")
                gold.add((idx, idx + len(value), etype))
                pos = idx + len(value)
            items.append((text, gold))
    return items


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate PII detection.")
    parser.add_argument("--data", default="eval_data.jsonl")
    parser.add_argument("--use-spacy", action="store_true")
    args = parser.parse_args(argv)

    items = load_gold(args.data)
    # per-type counters
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for text, gold in items:
        pred = {(h.start, h.end, h.type) for h in detect(text, use_spacy=args.use_spacy)}
        for span in pred & gold:
            stats[span[2]]["tp"] += 1
        for span in pred - gold:
            stats[span[2]]["fp"] += 1
        for span in gold - pred:
            stats[span[2]]["fn"] += 1

    types = sorted(set(stats) | {s[2] for _, g in items for s in g})
    print(f"{'TYPE':<12}{'PRECISION':>10}{'RECALL':>10}{'F1':>10}{'#GOLD':>8}")
    print("-" * 50)
    tot = {"tp": 0, "fp": 0, "fn": 0}
    for t in types:
        s = stats[t]
        p, r, f1 = prf(s["tp"], s["fp"], s["fn"])
        gold_n = s["tp"] + s["fn"]
        print(f"{t:<12}{p:>10.3f}{r:>10.3f}{f1:>10.3f}{gold_n:>8}")
        for k in tot:
            tot[k] += s[k]
    p, r, f1 = prf(tot["tp"], tot["fp"], tot["fn"])
    print("-" * 50)
    print(f"{'MICRO-AVG':<12}{p:>10.3f}{r:>10.3f}{f1:>10.3f}{tot['tp'] + tot['fn']:>8}")
    print(f"\nevaluated {len(items)} examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
