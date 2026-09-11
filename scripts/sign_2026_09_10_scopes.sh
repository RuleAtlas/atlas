#!/usr/bin/env bash
# Sign and commit the 2026-09-10 program ingestion scopes.
#
# Run from /Users/pavelmakarchuk/axiom-corpus on a release branch cut from main AFTER the
# program PRs (#670-#678) are merged, with AXIOM_CORPUS_INGEST_PRIVATE_KEY exported in
# this shell only (never written to a file). Tracked files must be clean; untracked
# data/corpus artifacts are expected.
#
# Order matters: the signer records HEAD and requires a clean tracked tree, and the
# signed manifest must describe committed artifact bytes. So: (1) force-add and commit
# the artifacts, (2) sign every scope against that commit, (3) commit the manifests.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
: "${AXIOM_CORPUS_INGEST_PRIVATE_KEY:?export AXIOM_CORPUS_INGEST_PRIVATE_KEY in this shell first}"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "tracked tree is dirty; commit or stash first" >&2; exit 1; }

PATTERN='2026-09-10'   # every coverage file whose version starts with this
mapfile -t COVERAGE < <(ls data/corpus/coverage/*/*/${PATTERN}*.json | sort)
echo "scopes: ${#COVERAGE[@]}"

scope_fields() {  # prints: jurisdiction document_class version
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["jurisdiction"], d["document_class"], d["version"])' "$1"
}

# 1. force-add artifacts (data/ is gitignored) and commit them.
for c in "${COVERAGE[@]}"; do
  read -r jur cls ver < <(scope_fields "$c")
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["complete"] is True, sys.argv[1]' "$c"
  git add -f "data/corpus/coverage/$jur/$cls/$ver.json" \
             "data/corpus/inventory/$jur/$cls/$ver.json" \
             "data/corpus/provisions/$jur/$cls/$ver.jsonl" \
             "data/corpus/sources/$jur/$cls/$ver"
done
git commit -q -m "$(printf 'Add 2026-09-10 program ingestion artifacts (unsigned data commit)\n\nSources, inventory, provisions and coverage for the LIHEAP, CCDF, SSI, Medicare, WIC,\nCHIP, Medicaid, TANF and tax scopes extracted on 2026-09-10. Signed ingest manifests\nfollow in the next commit.\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>')"
echo "data commit: $(git rev-parse --short HEAD)"

# 2. sign each scope against the clean data commit. The command text is the rebuild
#    command from the scope's run note (manifest path derived from the queue rows).
manifest_for() {  # best-effort lookup of the manifest that produced a scope
  python3 - "$1" "$2" "$3" <<'PY'
import sys, yaml, glob
jur, cls, ver = sys.argv[1:4]
for m in sorted(glob.glob("manifests/*.yaml")):
    try:
        d = yaml.safe_load(open(m))
    except Exception:
        continue
    if not isinstance(d, dict) or d.get("version") != ver:
        continue
    docs = d.get("documents") or []
    if docs and docs[0].get("jurisdiction") == jur and docs[0].get("document_class") == cls:
        print(m); break
else:
    print("")
PY
}
for c in "${COVERAGE[@]}"; do
  read -r jur cls ver < <(scope_fields "$c")
  m=$(manifest_for "$jur" "$cls" "$ver")
  cmd="axiom-corpus-ingest extract-official-documents --base data/corpus --version $ver"
  [ -n "$m" ] && cmd="$cmd --manifest $m"
  uv run axiom-corpus-ingest sign-ingest-manifest \
    --jurisdiction "$jur" --document-class "$cls" --version "$ver" \
    --command "$cmd (run note: docs/ingest-runs/2026-09-10-*.md)"
done

# 3. commit the signed manifests and self-check with the public key if available.
git add .axiom/ingest-manifests
git commit -q -m "$(printf 'Sign 2026-09-10 program ingestion scopes\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>')"
echo "sign commit: $(git rev-parse --short HEAD)"
if [ -n "${AXIOM_CORPUS_INGEST_PUBLIC_KEY:-}" ]; then
  uv run axiom-corpus-ingest guard-ingested --base-ref HEAD~2 --head-ref HEAD && echo "guard-ingested: ok"
else
  echo "AXIOM_CORPUS_INGEST_PUBLIC_KEY not set; CI will run guard-ingested on the PR"
fi
uv run axiom-corpus-ingest verify-scope-tracked --help >/dev/null 2>&1 && echo "next: verify-scope-tracked, then commit the release selector and run publish_corpus.py --dry-run"
