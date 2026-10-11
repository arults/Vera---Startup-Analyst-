# Vera company, round and evidence register v0.1.0

Read [REPORT.md](REPORT.md) for current counts and the next research queue.
Read [the schema and semantics](docs/COMPLETION_REGISTER_V1.md) before interpreting
completion labels. This is an additive seven-table import, not a completed study.

Python 3.10+; no third-party dependencies. From the repository root:

```sh
python -m unittest discover -s research/company-register-v0.1.0/tests -v
python research/company-register-v0.1.0/verify_release.py --root .
python research/company-register-v0.1.0/inspect_register.py
python research/company-register-v0.1.0/inspect_register.py --table lineage --limit 5
python research/company-register-v0.1.0/inspect_register.py --table source_coverage
```

A fresh build, reading existing repository files without changing them:

```sh
python research/company-register-v0.1.0/src/phase1d/completion_register.py \
  --root . \
  --config research/company-register-v0.1.0/source_manifest.json \
  --output /tmp/vera-register-build
```

The root must contain the original seven source files and the pinned study spec
from commit `717e7be8f6ee672815f69ef8d8885ff9a555055d`. Hash validation fails if
any are changed. The test fixture is an exact copy of that spec, not a new policy.
Use a new output directory for changed data/code; the CLI refuses to replace an
existing artifact with different bytes. Run the same command twice to verify
idempotent imports.
