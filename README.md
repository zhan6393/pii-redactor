# PII Redactor

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![regex](https://img.shields.io/badge/detection-regex-blue?style=flat-square)
![spaCy](https://img.shields.io/badge/NER-spaCy_optional-09A3D5?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

A CLI tool that detects and redacts personally identifiable information in
text — emails, phone numbers, credit-card numbers, Canadian SINs and US
SSNs — replacing each hit with a `[REDACTED:TYPE]` tag and printing a
per-type redaction report.

Detection is **pure regex with zero dependencies**; an optional spaCy NER
pass adds `PERSON` / `ORG` / `LOCATION` entities when spaCy is installed.

## Quickstart

```bash
# redact a file, print to stdout
python redact.py sample_input.txt

# redact with a per-type report
python redact.py sample_input.txt --report

# write redacted output to a file
python redact.py sample_input.txt -o redacted.txt --report

# pipe via stdin
echo "Call me at 416-555-0132" | python redact.py

# add spaCy NER entities (optional)
python redact.py notes.txt --use-spacy
```

## Example

Input (`sample_input.txt`):

```
Please process the refund for Jane Doe (jane.doe@example.com). Her phone
number is 416-555-0132 and her backup contact is +1 (647) 555-0198.

Her credit card on file ends with the full number 4111 1111 1111 1111.
For tax purposes we need her SIN 123-456-789 on record.
```

Output:

```
Please process the refund for Jane Doe ([REDACTED:EMAIL]). Her phone
number is [REDACTED:PHONE] and her backup contact is [REDACTED:PHONE].

Her credit card on file ends with the full number [REDACTED:CREDIT_CARD].
For tax purposes we need her SIN [REDACTED:SIN] on record.
```

Redaction report (`--report`):

```
[redaction report] 8 entities redacted:
  CREDIT_CARD: 1
  EMAIL: 2
  PHONE: 3
  SIN: 1
  SSN: 1
```

## Evaluation

`eval.py` scores the detector against a small **synthetic labeled dataset**
(`eval_data.jsonl`, 14 examples). A prediction counts only on exact
span + type match. Per-type precision / recall / F1:

```bash
python eval.py
```

```
TYPE         PRECISION    RECALL        F1   #GOLD
--------------------------------------------------
CREDIT_CARD      1.000     1.000     1.000       3
EMAIL            1.000     1.000     1.000       4
PHONE            1.000     1.000     1.000       5
SIN              1.000     1.000     1.000       3
SSN              1.000     1.000     1.000       1
--------------------------------------------------
MICRO-AVG        1.000     1.000     1.000      16
```

> Honest caveat: this is a tiny synthetic benchmark tuned around the regex
> patterns — it demonstrates the eval harness, not production-grade accuracy.
> Real-world PII detection needs broader patterns, context rules, and a
> labeled corpus from your domain.

## Design notes

- **Overlap resolution:** all pattern matches are collected, then resolved
  longest-first at each start offset — a 16-digit card number is never
  shredded into phone/SIN fragments.
- **spaCy is strictly optional:** `--use-spacy` degrades gracefully with a
  warning if spaCy or `en_core_web_sm` is missing. Install with
  `pip install spacy && python -m spacy download en_core_web_sm`.
- All sample data uses reserved/fictional values (`555` phone numbers,
  `4111 1111 1111 1111` test card, sequential SINs) — no real PII anywhere.

## Project structure

```
pii-redactor/
├── redact.py                 # CLI: detect + redact + report
├── eval.py                   # precision/recall/F1 harness
├── eval_data.jsonl           # synthetic labeled dataset (14 examples)
├── sample_input.txt          # demo input (fictional PII)
├── sample_output_expected.txt# expected redacted output
└── requirements.txt          # empty core; spacy optional
```
