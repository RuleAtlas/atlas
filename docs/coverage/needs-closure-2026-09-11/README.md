# Needs-driven closure check, 2026-09-11 corpus

Per program: `<program>-schema.yaml` (the law-derived needs schema), `<program>-matrix.csv` (one row per jurisdiction x element: jurisdiction, element, level, family, status, scope_version, citation_path, pe_modeled, evidence_note) and `<program>.md` (method, roll-ups, gaps, closers, elements beyond PolicyEngine).

## SSI, LIHEAP, Medicare (branch analysis/needs-closure-ssi-liheap-medicare)

| program | elements | cells | PRESENT | EXTRACTABLE | ABSENT | OUTREACH | REVIEW | PE does not model |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ssi | 131 | 6812 | 3291 | 3386 | 83 | 8 | 44 | 92 |
| liheap | 41 | 2132 | 712 | 1268 | 44 | 1 | 107 | 28 |
| medicare | 68 | 3536 | 1311 | 2132 | 7 | 18 | 68 | 38 |

Built by `build_ssi_liheap_medicare_matrices.py` (reads `data/corpus` read-only), checked by `verify_matrices.py`, reports by `write_reports.py`.
