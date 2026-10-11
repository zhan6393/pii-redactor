#!/usr/bin/env python3
"""PII redactor: detect and redact sensitive entities in text.

Core detection is pure-regex (no dependencies). An optional spaCy NER pass
adds PERSON / ORG / LOCATION detection when spaCy and a model are installed.

Detected entities are replaced with ``[REDACTED:TYPE]`` tags and a per-type
redaction report is printed.

Usage:
    python redact.py sample_input.txt
    python redact.py sample_input.txt -o redacted.txt --report
    echo "Call me at 416-555-0132" | python redact.py
    python redact.py notes.txt --use-spacy        # adds spaCy NER entities
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Entity patterns (regex core — no dependencies)
# ---------------------------------------------------------------------------
#
# Priority matters: patterns are evaluated longest-match-first at the same
# start offset so a 16-digit card number is not shredded into phone/SIN hits.

PATTERNS: dict[str, re.Pattern] = {
    # 13-19 digit card numbers, spaced or dashed: 4111 1111 1111 1111
    "CREDIT_CARD": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}(?:[- ]?\d{1,3})?\b"),
    # Canadian SIN: 123-456-789 / 123 456 789 / 123456789
    "SIN": re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{3}\b|\b\d{9}\b"),
    # US SSN: 123-45-6789
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Email addresses
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # North-American phone numbers: (416) 555-0132, 416-555-0132, +1 416 555 0132
    "PHONE": re.compile(
        r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
    ),
}


@dataclass
class Hit:
    start: int
    end: int
    type: str
    value: str


def _spacy_hits(text: str) -> list[Hit]:
    """Optional NER pass. Returns [] if spaCy or the model is unavailable."""
    try:
        import spacy
    except ImportError:
        print("[warn] spaCy not installed — skipping NER pass", file=sys.stderr)
        return []
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("[warn] spaCy model 'en_core_web_sm' not found — skipping NER pass",
              file=sys.stderr)
        print("       install it with: python -m spacy download en_core_web_sm",
              file=sys.stderr)
        return []
    label_map = {"PERSON": "PERSON", "ORG": "ORG", "GPE": "LOCATION", "LOC": "LOCATION"}
    return [
        Hit(ent.start_char, ent.end_char, label_map[ent.label_], ent.text)
        for ent in nlp(text).ents
        if ent.label_ in label_map
    ]


def detect(text: str, use_spacy: bool = False) -> list[Hit]:
    """Find all PII spans. Overlapping hits resolve longest-first."""
    hits: list[Hit] = []
    for etype, pattern in PATTERNS.items():
        hits.extend(Hit(m.start(), m.end(), etype, m.group()) for m in pattern.finditer(text))
    if use_spacy:
        hits.extend(_spacy_hits(text))
    # Sort by start, then longest first; greedily keep non-overlapping spans.
    hits.sort(key=lambda h: (h.start, -(h.end - h.start)))
    kept: list[Hit] = []
    last_end = -1
    for h in hits:
        if h.start >= last_end:
            kept.append(h)
            last_end = h.end
    return kept


def redact(text: str, use_spacy: bool = False) -> tuple[str, dict[str, int]]:
    """Return (redacted_text, {entity_type: count})."""
    hits = detect(text, use_spacy=use_spacy)
    out: list[str] = []
    pos = 0
    report: dict[str, int] = {}
    for h in hits:
        out.append(text[pos:h.start])
        out.append(f"[REDACTED:{h.type}]")
        report[h.type] = report.get(h.type, 0) + 1
        pos = h.end
    out.append(text[pos:])
    return "".join(out), report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect and redact PII in text.")
    parser.add_argument("input", nargs="?", help="Input file (default: stdin)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("--report", action="store_true",
                        help="Print per-type redaction counts to stderr")
    parser.add_argument("--use-spacy", action="store_true",
                        help="Add spaCy NER pass (PERSON/ORG/LOCATION)")
    args = parser.parse_args(argv)

    if args.input:
        text = open(args.input, encoding="utf-8").read()
    else:
        text = sys.stdin.read()

    redacted, report = redact(text, use_spacy=args.use_spacy)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(redacted)
    else:
        print(redacted, end="")

    if args.report:
        total = sum(report.values())
        print(f"\n[redaction report] {total} entities redacted:", file=sys.stderr)
        for etype in sorted(report):
            print(f"  {etype}: {report[etype]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
