# Program ingestion hand-off (2026-09-10 to 2026-09-11)

Controller hand-off for the board Year 1 program ingestion. Everything below is committed and
pushed to TheAxiomFoundation/axiom-corpus; nothing is signed or published. Corpus artifacts
(`data/corpus/{sources,inventory,provisions,coverage}`) exist only on the controller's machine
(`data/` is gitignored) and are unsigned.

## Branches and pull requests

| Program | Branch | Draft PR | Run notes (`docs/ingest-runs/`) |
| --- | --- | --- | --- |
| base: work orders + LIHEAP | `discovery/committed-program-work-orders` | #670 (to main) | `2026-09-10-liheap-state-plans-fy2026.md` |
| SSI | `discovery/ingest-ssi` | #671 | `2026-09-10-ssi-poms-si.md`, `2026-09-10-ssi-state-supplements-batch-{1,2,3}.md` |
| Medicare | `discovery/ingest-medicare` | #672 | `2026-09-10-medicare-cms-iom-100-01.md`, `-100-24.md` |
| Tax | `discovery/ingest-tax` | #673 | `2026-09-10-tax-forms-instructions-guidance-batch-{1,2,3-retry}.md` |
| CHIP | `discovery/ingest-chip` | #674 | `2026-09-10-chip-state-eligibility-manuals{,-batch-2,-batch-3,-batch-4-retry}.md` |
| TANF | `discovery/ingest-tanf` | #675 | `2026-09-10-tanf-state-policy-manuals-batch-{1,2,3,4-retry}.md` |
| WIC | `discovery/ingest-wic` | #676 | `2026-09-10-wic-fns-guidance-and-state-manuals.md`, `2026-09-10-wic-state-manuals-batch-{2,3,4-retry,5}.md` |
| CCDF | `discovery/ingest-ccdf` | #677 | `2026-09-10-ccdf-state-plans-fy2025-2027{,-retry,-retry-2}.md` |
| Medicaid | `discovery/ingest-medicaid` | #678 | `2026-09-10-medicaid-state-eligibility-manuals-batch-{1,2,3,4-retry,5}.md` |
| SNAP completion (#680) | `discovery/ingest-snap` | #681 | `2026-09-10-snap-state-manual-completion-batch-{1,2,3}.md` |

The program PRs are stacked on the base branch. CI only runs for PRs against `main`, so either
merge #670 first or retarget the program PRs to `main`. All generator scripts pass `ruff`.
Cross-branch pointers: CHIP rows for LA, OH, SC, KS, AZ, NC, NJ, VA, AR and SSI rows for TX, ID
point at Medicaid- or CHIP-branch scopes, so those branches must merge together.

## Per-jurisdiction state

Each program queue (`manifests/<program>-agent-queue.yaml`, `manifests/snap-completion-agent-queue.yaml`)
carries one row per jurisdiction with `queue_status` (`agent_ready` = extracted, `done` = already in
the corpus by pointer, `blocked_primary_source` = exact failure recorded, `needs_review`),
`index_url`, `index_document_count`, `taken_count`, and index families. Every run note lists every
reviewer judgment. Blocks that survive a US-exit network are publisher bot walls (NY OTDA/OCFS,
CA DHCS, AZ DES, MO, MD, GA, TX AWS WAF) or agencies that post no manual; they are not
worked around. Issue #680's "ingestion gap" for FL, AL, MD, MA is a counting artifact (ingested
regulation sections never queued for encoding), not lost documents; its thin states are now either
completed (TX, NH, KY, WY, ND) or confirmed complete against their publishers.

## Controller steps

1. Review and merge the PRs.
2. On a clean branch cut from `main` after the merges, with `AXIOM_CORPUS_INGEST_PRIVATE_KEY`
   exported in the shell (never in a file), run `scripts/sign_2026_09_10_scopes.sh`. It force-adds
   the artifacts and commits them, signs every `2026-09-10*` scope against that commit, commits the
   signed manifests under `.axiom/ingest-manifests/`, and self-verifies with `guard-ingested` when
   `AXIOM_CORPUS_INGEST_PUBLIC_KEY` is exported. Open a PR; CI runs `guard-ingested`.
3. Cut an immutable successor selector: the current US release's 275 scopes plus the 265 complete
   `2026-09-10*` scopes (88,199 provisions), 540 in total. A draft validated with
   `axiom-corpus-ingest validate-release --base data/corpus --release <selector> --ignore-r2-missing`.
   Resolve these errors first:
   - Colorado TANF `us-co/regulation/9-ccr-2503-6/3.606.{1,2,6}` duplicate the released
     `us-co/regulation/2026-07-13-recovery` paths with different text (drop the three sections,
     hold CO TANF out, or supersede the old scope).
   - The Ohio OAC and Maryland COMAR adapters emit shared container rows (`us-oh/regulation`,
     `us-md/regulation/title-07/...`) in every scope they build; the new OH TANF, OH SSI and
     MD SSI adapter scopes collide with each other and with the released OAC 5101:4 scope.
     Either the adapters stop emitting shared container rows or those scopes stay out.
   - Advisory `unsectioned_document_body` warnings (GA, IA, KY, MD, OR single-body documents) can
     be split later with `section-provisions`.
4. `uv run --extra dev python scripts/publish_corpus.py --release manifests/releases/<name>.json --dry-run`,
   then dispatch `activate-release.yml` and approve the `release-preview` and `release-activation`
   environments.

## Final per-jurisdiction tally

Extracted / done by pointer / blocked, over the 50 states plus DC: LIHEAP 51/0/0 · Medicaid 41/6/3
(AL, CA, NE; WY needs_review) · CCDF 43/0/6 (AZ, GA, MD, MO, NY, TX; AK and IN post no conforming plan)
· CHIP 33/13/5 (CA, DC, FL, MT, WY) · SSI 27/22/2 (NY, WY) · TANF 24/26/1 (NY) · WIC 21/0/30 (7 access
blocks, 3 behind login, 20 publish no manual) · tax 17/34/0 · SNAP completion 5/20/3 (AZ, NY,
OH eManuals) · Medicare federal only (IOM Pub 100-01 and Pub 100-24). Every jurisdiction has a resolved
row in every program queue.

## Open reviewer decisions

- `manual` vs `regulation` for codified rules ingested as `manual` under the work order (NJ, MA, CO,
  OK, OH, NM Medicaid); precedents used `regulation`.
- Texas Works Handbook Part A text sits in both the Medicaid scope and the SNAP completion scope
  under different path conventions.
- Revised editions found during the SNAP completion pass (NC, GA, TN, OK, MI, KY, NE, AR, NV, WY,
  ND, ME) need superseding scopes; released scopes are immutable.
- WIC DC `source_as_of` is 2026-09-11 while the other WIC scopes carry 2026-09-10.
