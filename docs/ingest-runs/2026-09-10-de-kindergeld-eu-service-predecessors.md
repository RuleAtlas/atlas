# Original EU service-programme sources

This capture retains the complete original German Official Journal texts of
Regulation (EU) 2018/1475 (20 pages, OJ L 250/1–20 of 4 October 2018) and
Regulation (EU) No 1288/2013 (24 pages, OJ L 347/50–73 of 20 December 2013).
The adult-child source review identified these predecessor programmes in
DA-KG A18.4. Both PDFs come directly from EUR-Lex and match the SHA-256 values
recorded in the manifest and companion audit. The existing native
`extract-official-documents` adapter captures each complete document as one
content block plus its document root. Coverage is four of four rows, with
no missing or extra citation. No source body or generated row was manually edited.

Identity, page counts, extractable text on every page, title, article/signature
and final-annex boundaries were inspected. This is capture QA, not a legal
review of every article or all 44 pages. The original expressions are not
current consolidated texts. Amendments, repeal/transition rules and the
continuation of individual service activities require separate review before
encoding historical applicability. No programme-membership Boolean or
Kindergeld eligibility result is encoded by this capture.

Reproduce from the repository root:

```bash
PYTHONPATH=src axiom-corpus-ingest extract-official-documents --base data/corpus --version 2026-09-10-de-kindergeld-eu-service-predecessors --manifest manifests/de-kindergeld-eu-service-predecessors.yaml
```

The additive release selector preserves all 46 preceding DE scopes and adds
this scope, for 47 scopes and 9,866 provision rows. Publication and serving
activation are separate; this work does not activate serving.
