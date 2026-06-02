# hotel-business-data

Minimal hotel business data processing workspace for Codex cloud checks.

## Purpose

This repository is prepared for lightweight hotel operations data workflows such as:

- validating synthetic sample datasets;
- checking Python dependency availability;
- writing generated reports to `output/`;
- keeping real customer data out of source control.

## Data policy

Do **not** commit real customer data, real phone numbers, real commission records, or other sensitive business information.
Use only synthetic or anonymized data in `data_sample/`.

## Quick environment check

```bash
python -m pip install -r requirements.txt
python scripts/test_env.py
```

The environment check validates expected repository paths, imports configured dependencies, reads the synthetic sample CSV, and writes a small JSON status report under `output/`.
