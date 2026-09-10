"""Build the SNAP state-manual completion manifests (axiom-corpus#680, batch 1) and the
completion queue `manifests/snap-completion-agent-queue.yaml`.

Issue #680 splits the thin SNAP states into an ingestion gap (FL, AL, MD, MA: more documents
registered in manifests than "captured") and a discovery gap (TX, CA, NY, NH, KY, ME, ...:
little registered). Released SNAP scopes are immutable, so every document that is missing
from the corpus goes into a NEW scope per state:

    jurisdiction us-xx, document_class per the state's existing convention,
    version 2026-09-10-snap-state-manual-completion,
    manifest manifests/us-xx-snap-manual-completion.yaml.

Every document is confirmed from the publisher's own index, fetched live here so the manifest
reflects what the publisher lists today. Nothing is taken from mirrors, archives or compiled
lists, and a citation path that already exists in any provisions JSONL of the corpus
(`--corpus-base`) is skipped and recorded, because a release rejects duplicate citation paths.

    uv run python scripts/build_snap_state_manual_completion_manifests.py \
        --corpus-base /path/to/axiom-corpus/data/corpus          # both live builders
    uv run python scripts/build_snap_state_manual_completion_manifests.py --only us-tx

Live builders: us-tx (Texas Works Handbook Parts A-C and glossary on fhb.hhs.texas.gov) and
us-nh (DHHS Food Stamp Manual WebHelp on www.dhhs.nh.gov). The other eight batch-1 states are
static rows: FL, AL, MD, MA (diagnosed, nothing failed to land), CA and ME (publisher index
confirmed complete), KY and NY (publisher blocked). See
docs/ingest-runs/2026-09-10-snap-state-manual-completion-batch-1.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "manifests" / "snap-completion-agent-queue.yaml"
VERSION = "2026-09-10-snap-state-manual-completion"
SOURCE_AS_OF = dt.date.today().isoformat()
EXPRESSION_DATE = SOURCE_AS_OF  # current-effective manual trees as fetched; see run note
UA = "Axiom/1.0 (Legal Archive; contact@axiom-foundation.org) https://github.com/TheAxiomFoundation/axiom-corpus"
ISSUE = "https://github.com/TheAxiomFoundation/axiom-corpus/issues/680"
RUN_NOTE = "docs/ingest-runs/2026-09-10-snap-state-manual-completion-batch-1.md"

_LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


def fetch(url: str, *, session: requests.Session | None = None) -> str:
    """GET with TLS verification on; retry only transient connection errors."""
    client = session or requests
    for attempt in range(4):
        try:
            resp = client.get(url, headers={"User-Agent": UA}, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.ConnectionError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_impersonated(url: str, *, timeout: int = 20) -> tuple[int, bytes]:
    """GET through curl-cffi browser impersonation (the existing manifest option
    `request: browser_impersonation: true`); TLS verification stays on."""
    from curl_cffi import requests as curl_requests

    resp = curl_requests.get(url, impersonate="chrome120", timeout=timeout)
    return resp.status_code, resp.content


def links(page: str, base: str) -> list[tuple[str, str]]:
    """Return (absolute href, text) pairs in document order, de-duplicated."""
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for href, text in _LINK_RE.findall(page):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(text))).strip()
        href = html.unescape(href).strip()
        absolute = urljoin(base, href).split("#", 1)[0]
        if (absolute, text) in seen:
            continue
        seen.add((absolute, text))
        out.append((absolute, text))
    return out


def slug(value: str, limit: int = 100) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:limit].strip("-")


def registered_citation_paths(*manifests: str) -> set[str]:
    """Citation paths already registered in the named (released, immutable) manifests."""
    paths: set[str] = set()
    for name in manifests:
        payload = yaml.safe_load((ROOT / "manifests" / name).read_text())
        paths.update(str(d["citation_path"]) for d in payload.get("documents", []))
    return paths


def corpus_citation_paths(corpus_base: Path | None, jurisdiction: str) -> set[str]:
    """Every citation_path in every provisions JSONL of the jurisdiction (all document
    classes, all versions). Empty when no corpus base is available (sparse worktree)."""
    if corpus_base is None:
        return set()
    paths: set[str] = set()
    for jsonl in sorted((corpus_base / "provisions" / jurisdiction).glob("*/*.jsonl")):
        with jsonl.open() as handle:
            for line in handle:
                if line.strip():
                    paths.add(json.loads(line)["citation_path"])
    return paths


# --------------------------------------------------------------------------- Texas


def build_tx() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Texas Works Handbook (TWH) on fhb.hhs.texas.gov, the publisher's own handbook host
    (www.hhs.texas.gov/handbooks/texas-works-handbook redirects there).

    Pages carry either policy text (``article.c-article div.c-field--name-body``) or only a
    "Pages in this section" sub-menu (``.c-view--hb-submenus``); many carry both. Text-bearing
    pages become documents; menu-only pages are counted as landing pages. Parts A (Determining
    Eligibility), B (Case Management) and C (Appendix) govern SNAP alongside TANF and Medicaid
    and are taken with the TWH Glossary; Parts D-X are medical-program-only parts and are
    inventoried, not taken. Sections already in the released TX scopes keep their citation paths
    and are skipped (inventoried as ``twh_section_already_in_released_scope``).
    """
    from bs4 import BeautifulSoup

    host = "https://fhb.hhs.texas.gov"
    twh = host + "/handbooks/texas-works-handbook"
    manual = "Texas Works Handbook"
    existing = registered_citation_paths("us-tx-manuals.yaml", "us-tx-twh-c120-snap-deduction-amounts.yaml")
    session = requests.Session()
    families: dict[str, dict[str, int]] = {}
    docs: list[dict[str, Any]] = []
    seen: set[str] = set()
    taken_parts = {"part-a-determining-eligibility": "a", "part-b-case-management": "b", "part-c-appendix": "c"}

    def document_for(url: str, title: str) -> dict[str, Any]:
        section = url.rsplit("/", 1)[-1]
        return {
            "source_id": f"tx-hhs-texas-works-{section}",
            "jurisdiction": "us-tx",
            "document_class": "manual",
            "citation_path": f"us-tx/manual/hhs/texas-works-handbook/{section}",
            "title": f"{manual}: {title}",
            "source_url": url,
            "source_format": "html",
            "source_as_of": SOURCE_AS_OF,
            "expression_date": EXPRESSION_DATE,
            "extraction": {
                "html_content_selector": "article.c-article div.c-field--name-body",
                "html_drop_selectors": [".c-field__label"],
            },
            "metadata": {
                "primary_source": True,
                "source_authority": "Texas Health and Human Services Commission",
                "document_subtype": "handbook_section",
                "program": "SNAP",
                "state_program": "Texas Works (SNAP, TANF and Medicaid for children and families)",
                "federal_program": "SNAP",
                "manual": manual,
                "manual_landing_page": twh,
                "source_discovery_group": "us-tx/manual/snap",
                "discovered_via": f"manual-review:snap-completion-agent-queue batch 1 ({ISSUE}); publisher index {twh}",
            },
        }

    def crawl(start: str, *, part: str) -> None:
        fam = families.setdefault(f"twh_part_{part}_section_html", {"found": 0, "taken": 0})
        landing = families.setdefault(f"twh_part_{part}_section_landing_html", {"found": 0, "taken": 0})
        already = families.setdefault("twh_section_already_in_released_scope", {"found": 0, "taken": 0})
        label_re = re.compile(re.escape(twh) + rf"/({part}-\d{{3,4}})-")
        queue = [start]
        while queue:
            url = queue.pop(0)
            if url in seen or not url.startswith(twh + "/"):
                continue
            seen.add(url)
            soup = BeautifulSoup(fetch(url, session=session), "html.parser")
            heading = soup.select_one("h1.c-page-title")
            title = re.sub(r"\s+", " ", heading.get_text(" ", strip=True)) if heading else url.rsplit("/", 1)[-1]
            children = [urljoin(url, str(a["href"])).split("#", 1)[0] for a in soup.select(".c-view--hb-submenus a[href]")]
            queue.extend(children)
            if url == start or label_re.match(url) is None:
                landing["found"] += 1
                continue
            if soup.select_one("article.c-article div.c-field--name-body") is None:
                landing["found"] += 1
                continue
            doc = document_for(url, title)
            if doc["citation_path"] in existing:
                already["found"] += 1
                continue
            fam["found"] += 1
            fam["taken"] += 1
            docs.append(doc)

    index_page = fetch(twh, session=session)
    parts = [(h, t) for h, t in links(index_page, twh) if h.startswith(twh + "/part-")]
    families["twh_part_landing_html"] = {"found": len(parts), "taken": 0}
    for phref, ptext in parts:
        part_slug = phref.rsplit("/", 1)[-1]
        if part_slug in taken_parts:
            crawl(phref, part=taken_parts[part_slug])
            continue
        letter = part_slug.split("-", 2)[1]
        chapters = {h for h, _ in links(fetch(phref, session=session), phref) if re.match(re.escape(twh) + rf"/{letter}-\d{{3,4}}-", h)}
        families[f"twh_{slug(ptext.split(',')[0])}_chapters_html"] = {"found": len(chapters), "taken": 0}
    glossary = twh + "/twh-glossary"
    glossary_doc = document_for(glossary, "TWH Glossary")
    glossary_doc["source_id"] = "tx-hhs-texas-works-twh-glossary"
    glossary_doc["citation_path"] = "us-tx/manual/hhs/texas-works-handbook/twh-glossary"
    families["twh_glossary_html"] = {"found": 1, "taken": 1}
    docs.append(glossary_doc)
    other = [t for h, t in links(index_page, twh) if h.startswith(twh + "/twh-") and h != glossary]
    families["twh_forms_documents_notices_revisions_bulletins_contact_pages"] = {"found": len(set(other)), "taken": 0}
    return docs, {"index_url": twh, "families": families, "existing_citation_paths_skipped": sorted(existing)}


# --------------------------------------------------------------------------- New Hampshire


def build_nh() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """New Hampshire DHHS Food Stamp Manual (RoboHelp WebHelp at www.dhhs.nh.gov/fsm_htm/),
    linked as "Food Stamp/SNAP Policy Manual" from the DHHS SNAP program page.

    The host answers HTTP 403 to the plain Axiom request and HTTP 200 to the existing manifest
    option ``browser_impersonation`` (curl-cffi chrome120); the manifest therefore carries that
    option, exactly as the NH Family Assistance Manual scope does. Topics are enumerated from the
    WebHelp plain-HTML table of contents (``whgdata/whlstt0.htm`` ... until 404), de-duplicated by
    topic file (the TOC lists a topic under several books), and every topic is fetched once to
    confirm it answers 200 and to inventory the Service Release (SR) documents it cites
    (``../../sr_htm/html/sr_*.htm``), which are a separate document family, not taken.
    """
    base = "https://www.dhhs.nh.gov/fsm_htm/"
    landing = base + "newfsm.htm"
    manual = "New Hampshire Food Stamp Manual"
    families: dict[str, dict[str, int]] = {}
    toc_pages: list[tuple[str, str]] = []
    for i in range(0, 500):
        toc_url = f"{base}whgdata/whlstt{i}.htm"
        status, content = fetch_impersonated(toc_url)
        if status != 200:
            break
        toc_pages.append((f"whlstt{i}.htm", content.decode("utf-8", "replace")))
    families["webhelp_toc_pages_html"] = {"found": len(toc_pages), "taken": 0}

    topics: dict[str, tuple[str, str]] = {}
    toc_links = 0
    for toc_file, page in toc_pages:
        for href, text in _LINK_RE.findall(page):
            href = html.unescape(href).strip()
            if href.startswith("whlstt"):
                continue
            toc_links += 1
            absolute = urljoin(f"{base}whgdata/", href).split("#", 1)[0]
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(text))).strip()
            topics.setdefault(absolute, (text, toc_file))
    families["webhelp_toc_links"] = {"found": toc_links, "taken": 0}

    def probe(url: str) -> tuple[str, int, set[str]]:
        status, content = fetch_impersonated(url)
        text = content.decode("utf-8", "replace") if status == 200 else ""
        srs = {urljoin(url, html.unescape(h)).split("#", 1)[0] for h in re.findall(r'href="([^"]*sr_htm/[^"]+)"', text)}
        return url, status, srs

    with ThreadPoolExecutor(max_workers=6) as pool:
        probes = {url: (status, srs) for url, status, srs in pool.map(probe, sorted(topics))}
    service_releases: set[str] = set()
    docs: list[dict[str, Any]] = []
    fam = families.setdefault("food_stamp_manual_topic_html", {"found": 0, "taken": 0})
    unreachable = families.setdefault("food_stamp_manual_topic_unreachable", {"found": 0, "taken": 0})
    for url in sorted(topics, key=lambda u: (topics[u][1], u)):
        title, toc_file = topics[url]
        status, srs = probes[url]
        service_releases |= srs
        if status != 200:
            unreachable["found"] += 1
            print(f"us-nh: topic {url} answered HTTP {status}; not taken", file=sys.stderr)
            continue
        stem = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        label = slug(stem)
        fam["found"] += 1
        fam["taken"] += 1
        docs.append(
            {
                "source_id": f"us-nh-dhhs-fsm-{label}",
                "jurisdiction": "us-nh",
                "document_class": "manual",
                "title": f"{manual}: {title}",
                "source_url": url,
                "source_format": "html",
                "source_as_of": SOURCE_AS_OF,
                "expression_date": EXPRESSION_DATE,
                "citation_path": f"us-nh/manual/dhhs/fsm/{label}",
                "request": {"browser_impersonation": True},
                "extraction": {"html_drop_selectors": ["#header", ".no-print", ".navBtnCusStyle"]},
                "metadata": {
                    "primary_source": True,
                    "source_authority": "New Hampshire Department of Health and Human Services, Bureau of Family Assistance",
                    "document_subtype": "policy_manual_topic",
                    "program": "SNAP",
                    "federal_program": "SNAP",
                    "manual": manual,
                    "manual_landing_page": landing,
                    "manual_toc_url": f"{base}whgdata/whlstt0.htm",
                    "toc_file": toc_file,
                    "source_discovery_group": "us-nh/manual/snap",
                    "discovered_via": (
                        f"manual-review:snap-completion-agent-queue batch 1 ({ISSUE}); DHHS SNAP program page "
                        "https://www.dhhs.nh.gov/programs-services/food-meals-assistance/supplemental-nutrition-assistance-program-snap "
                        f"links the manual at {landing}"
                    ),
                },
            }
        )
    families["service_release_html_cited_by_topics"] = {"found": len(service_releases), "taken": 0}
    return docs, {"index_url": landing, "families": families}


# --------------------------------------------------------------------------- queue rows

BUILDERS = {"us-tx": build_tx, "us-nh": build_nh}
NAMES = {
    "us-fl": "Florida", "us-al": "Alabama", "us-md": "Maryland", "us-ma": "Massachusetts", "us-tx": "Texas",
    "us-ca": "California", "us-ny": "New York", "us-nh": "New Hampshire", "us-ky": "Kentucky", "us-me": "Maine",
}
SOURCE_KIND = {"us-tx": "official_html_handbook_sections", "us-nh": "official_html_webhelp_manual_topics"}
BATCH_NOTE = (
    "Batch 1 (2026-09-10, axiom-corpus#680): ingestion-gap states FL, AL, MD, MA diagnosed against the released "
    "scopes, then discovery-gap states TX, CA, NY, NH, KY, ME checked on the publisher's own index. Generator: "
    "scripts/build_snap_state_manual_completion_manifests.py."
)

STATIC_ROWS: dict[str, dict[str, Any]] = {
    "us-fl": {
        "queue_status": "done",
        "source_kind": "official_pdf_manual_sections",
        "primary_source_url": "https://www.myflfamilies.com/services/public-assistance/additional-resources-and-services/ess-program-manual",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-fl", "document_class": "manual", "version": "2026-05-27-fl-ess-manual-r2026-07-15-self-contained"},
        "index_url": "https://www.myflfamilies.com/services/public-assistance/additional-resources-and-services/ess-program-manual",
        "index_document_count": 76, "taken_count": 0,
        "index_families": {"ess_program_policy_manual_section_pdf": {"found": 48, "taken": 0, "already_in_corpus": 48},
                           "ess_summary_of_changes_quarterly_pdf": {"found": 28, "taken": 0}},
        "notes": (
            "Diagnosis 2026-09-10 (#680 says 68 registered, 48 captured): nothing failed to land. 'Registered' counts manifests whose "
            "program tag is SNAP: the 68 are manifests/us-fl-snap-primary-policy.yaml, FAC 65A-1 sections republished by Cornell LII "
            "(metadata primary_source: false), all 68 roots present in the released scope us-fl/regulation/2026-05-29-r2026-07-15-self-contained "
            "(204 provisions, coverage complete). 'Captured' is the encoding queue plus rulespec artifacts: the 48 are the DCF ESS Program "
            "Policy Manual PDFs (manifests/us-fl-ess-manual.yaml, program tag ESS, so not counted as SNAP-registered), all 48 roots present in "
            "us-fl/manual/2026-05-27-fl-ess-manual-r2026-07-15-self-contained (1,107 provisions, coverage complete). The difference is 61 "
            "registered-and-ingested regulation sections that sit in no encoding queue and have no artifact (dashboard stalled_registered), "
            "not an extraction, scope-cut or selector failure. Publisher index today: 76 PDF links = the same 48 manual sections plus 28 "
            "quarterly Summary of Changes PDFs (separate change-summary family, not taken). No completion scope needed. Reviewer: the "
            "Cornell LII regulation manifest is a non-primary republication under this queue's forbidden-sources policy; replacing it with "
            "the official flrules.org FAC 65A-1 text is a separate work order."
        ),
    },
    "us-al": {
        "queue_status": "done",
        "source_kind": "official_pdf_chapter_manual",
        "primary_source_url": "https://apps.dhr.alabama.gov/POE/POEhome",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-al", "document_class": "manual", "version": "2026-05-27-al-snap-poe-manual-r2026-07-15-self-contained"},
        "index_url": "https://apps.dhr.alabama.gov/POE/POEhome",
        "index_document_count": None, "taken_count": 0,
        "index_families": {"poe_manual_chapter_pdf": {"found": 17, "taken": 0, "already_in_corpus": 17}},
        "notes": (
            "Diagnosis 2026-09-10 (#680 says 59 registered, 17 captured): nothing failed to land. Registered 59 = 42 Ala. Admin. Code 660-4 "
            "sections republished by Cornell LII (manifests/us-al-snap-primary-policy.yaml, primary_source: false; all 42 roots present in the "
            "released scope us-al/regulation/2026-05-29-r2026-07-15-self-contained, 126 provisions) + the 17 DHR POE Online Manual chapter PDFs "
            "(manifests/us-al-snap-manual.yaml; all 17 roots present in us-al/manual/2026-05-27-al-snap-poe-manual-r2026-07-15-self-contained, "
            "149 provisions, coverage complete). Captured 17 = the POE chapters in the encoding queue; the 42 regulation sections are ingested "
            "but in no queue (dashboard stalled_registered 20 after de-duplication against artifacts). Publisher index re-check blocked today: "
            "apps.dhr.alabama.gov TCP connect timeout (curl 28 after 30 s plain request; curl-cffi chrome120 the same after 20 s); the 17-chapter "
            "inventory stands from the queue row of 2026-05-27. No completion scope needed."
        ),
    },
    "us-md": {
        "queue_status": "done",
        "source_kind": "official_pdf_or_html_manual",
        "primary_source_url": "https://dhs.maryland.gov/supplemental-nutrition-assistance-program/food-supplement-program-manual/",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-md", "document_class": "manual", "version": "2026-07-17-md-snap-manual"},
        "index_url": "https://dhs.maryland.gov/supplemental-nutrition-assistance-program/food-supplement-program-manual/",
        "index_document_count": 51, "taken_count": 0,
        "index_families": {"snap_manual_section_file": {"found": 51, "taken": 0, "already_in_corpus": 51}},
        "notes": (
            "Diagnosis 2026-09-10 (#680 says 54 registered, 53 captured): nothing failed to land. Registered 54 = 51 manual files "
            "(manifests/us-md-fsp-manual.yaml; all 51 roots present in the released scope us-md/manual/2026-07-17-md-snap-manual, 379 "
            "provisions, coverage complete) + 3 FIA FY2026 SNAP guidance documents (manifests/us-md-fia-snap-fy2026-guidance.yaml, released "
            "scope us-md/guidance/2026-07-12-md-fia-snap-fy2026). Captured 53 = 51 queue items + 2 rulespec artifacts; the 1-document gap is "
            "a guidance row with no queue item or artifact. Publisher index today lists exactly the same 51 files (0 new, 0 removed). No "
            "completion scope needed."
        ),
    },
    "us-ma": {
        "queue_status": "done",
        "source_kind": "official_regulations",
        "primary_source_url": "https://www.mass.gov/lists/department-of-transitional-assistance-regulations",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-ma", "document_class": "regulation", "version": "2026-07-21-ma-dta-regulations-consolidated"},
        "index_url": "https://www.mass.gov/lists/department-of-transitional-assistance-regulations",
        "index_document_count": 18, "taken_count": 0,
        "index_families": {"dta_snap_regulation_chapter_pdf": {"found": 9, "taken": 0, "already_in_corpus": 9},
                           "dta_snap_regulation_chapter_docx_duplicate": {"found": 9, "taken": 0}},
        "notes": (
            "Diagnosis 2026-09-10 (#680 says 54 registered, 12 captured): nothing failed to land. Registered 54 = 44 106 CMR 364-365 sections "
            "republished by Cornell LII (manifests/us-ma-snap-primary-policy.yaml, primary_source: false) + 9 official DTA chapter files "
            "(343, 360-367; manifests/us-ma-dta-snap-regulations.yaml) + 1 COLA guidance document. 53 of the 54 registered citation paths are "
            "present in the released consolidated scope us-ma/regulation/2026-07-21-ma-dta-regulations-consolidated (332 provisions; the 9 "
            "chapter roots all present). The one absent path, us-ma/regulation/106-cmr/364/360, is a Cornell LII manifest entry for a "
            "section number the official chapter 364 PDF does not carry, so it is not a missing official document. Captured 12 = 9 queue items "
            "+ 3 artifacts; the remainder is ingested-but-unqueued. Publisher index today: the same 9 chapter PDFs (all in the manifest) plus a "
            "DOCX copy of each chapter (same text, other format; not taken). The DTA Online Guide named in #680 "
            "(https://www.mass.gov/info-details/the-department-of-transitional-assistance-online-guide) is a separate manual family whose "
            "index page carries only in-page anchors and DTA Connect links; it is not an ingestion gap and is left for a discovery batch. No "
            "completion scope needed."
        ),
    },
    "us-ca": {
        "queue_status": "done",
        "source_kind": "official_docx_and_ocr_pdf_manual_regulations",
        "primary_source_url": "https://www.cdss.ca.gov/inforesources/letters-regulations/legislation-and-regulations/calworks-calfresh-regulations/calfresh-regulations",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-ca", "document_class": "regulation", "version": "2026-07-17-ca-cdss-mpp-calfresh"},
        "index_url": "https://www.cdss.ca.gov/inforesources/letters-regulations/legislation-and-regulations/calworks-calfresh-regulations/calfresh-regulations",
        "index_document_count": 15, "taken_count": 0,
        "index_families": {"mpp_division_63_food_stamp_manual_file": {"found": 15, "taken": 0, "already_in_corpus": 15}},
        "notes": (
            "Index confirmed 2026-09-10: the CDSS CalFresh Regulations page (the publisher's own index of the Manual of Policies and "
            "Procedures Division 63) lists 15 Food Stamp Manual files (fsman01-fsman12 incl. 04a/04b and 11a/11b/11c); all 15 are in "
            "manifests/us-ca-cdss-mpp-calfresh-complete.yaml and the released scope us-ca/regulation/2026-07-17-ca-cdss-mpp-calfresh (436 "
            "provisions, coverage complete). CDSS publishes no separate CalFresh handbook; county handbooks are not state primary sources. "
            "#680's 18 'captured' = 15 queue items + 3 artifacts, i.e. a document count, not a section count. Nothing new to take."
        ),
    },
    "us-me": {
        "queue_status": "done",
        "source_kind": "official_agency_rules",
        "primary_source_url": "https://www.maine.gov/sos/rulemaking/agency-rules/department-health-and-human-services-rules",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-me", "document_class": "regulation", "version": "2026-07-17-me-snap-rules"},
        "index_url": "https://www.maine.gov/sos/rulemaking/agency-rules/department-health-and-human-services-rules",
        "index_document_count": 3, "taken_count": 0,
        "index_families": {"ofi_snap_rule_chapter_docx": {"found": 2, "taken": 0, "already_in_corpus": 2},
                           "ofi_sun_bucks_rule_chapter_docx": {"found": 1, "taken": 0}},
        "notes": (
            "Index confirmed 2026-09-10: the Secretary of State DHHS rules index lists 10-144 Ch. 301 (SNAP Rules, file "
            "144c301-2026-133-NSC.docx, the same file as the released scope), Ch. 609 (SNAP Employment and Training) and Ch. 302 (SUN Bucks, "
            "a Summer EBT program, outside SNAP). Both SNAP chapters are in manifests/us-me-snap-rules.yaml and the released scope "
            "us-me/regulation/2026-07-17-me-snap-rules (223 provisions). Reviewer: the index now links Ch. 609 as 144c609-2026-191-AMD.docx, "
            "an amended edition newer than the released 144c609_0.docx; its citation path us-me/regulation/dhhs/ofi/chapter-609 already exists, "
            "so a completion scope cannot carry it and a superseding ME rules scope is needed instead. #680's 2 'captured' is a document count "
            "(two rulebooks), not a section count. Nothing new to take here."
        ),
    },
    "us-ky": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_agency_page",
        "primary_source_url": "https://www.chfs.ky.gov/agencies/dcbs/dfs/Pages/default.aspx",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-ky", "document_class": "manual", "version": "2026-07-17-ky-snap-manual"},
        "index_url": "https://www.chfs.ky.gov/agencies/dcbs/dfs/Pages/default.aspx",
        "index_document_count": None, "taken_count": 0,
        "index_families": {},
        "notes": (
            "Blocked 2026-09-10: the DCBS Division of Family Support page (the publisher index that lists the Operation Manual volumes) "
            "returns HTTP 403 (1,484-byte error page) to the plain Axiom request and the same HTTP 403 to curl-cffi chrome120 browser "
            "impersonation (20 s timeout). No workaround attempted. The released scope us-ky/manual/2026-07-17-ky-snap-manual already holds "
            "Volume II (SNAP) and Volume IIA (SNAP work requirements) in full (400 page provisions), so #680's 2 'captured' is a document count; "
            "the index re-check for newer OMTL editions or further SNAP volumes is what is blocked."
        ),
    },
    "us-ny": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_pdf_manuals",
        "primary_source_url": "https://otda.ny.gov/programs/snap/",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-ny", "document_class": "manual", "version": "2026-07-17-ny-snap-manuals"},
        "index_url": "https://otda.ny.gov/programs/snap/",
        "index_document_count": None, "taken_count": 0,
        "index_families": {},
        "notes": (
            "Blocked 2026-09-10: otda.ny.gov resets the plain Axiom request (curl 56, connection reset by peer, 30 s timeout) and answers "
            "curl-cffi chrome120 browser impersonation with HTTP 200 carrying a 5,609-byte F5/TSPD JavaScript bot-challenge page instead of the "
            "SNAP program page, so no index inventory is possible. No workaround attempted (the released scope's pinned official-URL archive "
            "captures are not an option for new documents under this run's rules). The released scopes already hold the 576-page SNAP Source "
            "Book, the 16-part Employment Policy Manual (340 provisions) and 18 NYCRR Parts 385 and 387 (1,678 provisions); #680's 18 'captured' "
            "is a document count. OTDA policy directives (ADM/INF/GIS) remain a separate family to inventory when the host answers."
        ),
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], metavar="JURISDICTION",
                        help="restrict live builders to these jurisdictions (static rows are still applied)")
    parser.add_argument("--corpus-base", type=Path, default=None,
                        help="corpus root whose provisions JSONL are scanned for citation paths that already exist "
                             "(skipped and recorded); omit in a sparse worktree without data/corpus")
    args = parser.parse_args()
    corpus_base = args.corpus_base
    if corpus_base is not None and not (corpus_base / "provisions").is_dir():
        print(f"--corpus-base {corpus_base} has no provisions directory", file=sys.stderr)
        return 1

    queue = yaml.safe_load(QUEUE.read_text()) if QUEUE.exists() else {
        "version": "2026-09-10",
        "document_family": "state_snap_policy_sources",
        "program": "SNAP",
        "queue_status": "in_progress",
        "policy": {
            "canonical_pipeline": "source-first",
            "source_policy": "primary_official_only",
            "durable_artifacts": ["sources", "inventory", "provisions", "coverage"],
            "forbidden_sources": ["secondary summaries", "State Options Reports", "benefitswiki",
                                  "policy manuals reposted by non-government sites", "mirrors, proxies and archived copies of blocked publishers"],
            "notes": [
                f"Completion pass for {ISSUE} (SNAP discovery missed ~24 states). The 51-row manifests/state-snap-manual-agent-queue.yaml "
                "stays as released; this queue tracks the per-state completion rows.",
                "Released SNAP scopes are immutable. Missing documents go into new per-state scopes, version "
                f"{VERSION}, manifests/us-xx-snap-manual-completion.yaml, document_class per the state's existing convention.",
                "A release rejects duplicate citation paths across scopes: every new document's citation path is checked against every "
                "provisions JSONL of its jurisdiction before it is taken.",
            ],
        },
        "states": [],
    }
    rows = {s["jurisdiction"]: s for s in queue.get("states", [])}
    summary: dict[str, Any] = {}
    for jur, build in BUILDERS.items():
        if args.only and jur not in args.only:
            continue
        docs, info = build()
        if not docs:
            print(f"{jur}: no documents found; index layout changed?", file=sys.stderr)
            return 1
        in_corpus = corpus_citation_paths(corpus_base, jur)
        skipped = sorted(d["citation_path"] for d in docs if d["citation_path"] in in_corpus)
        if skipped:
            docs = [d for d in docs if d["citation_path"] not in in_corpus]
            info["families"]["citation_path_already_in_corpus"] = {"found": len(skipped), "taken": 0}
            info["citation_paths_already_in_corpus"] = skipped
            print(f"{jur}: {len(skipped)} citation paths already in the corpus, skipped: {skipped[:10]}", file=sys.stderr)
        paths = [d["citation_path"] for d in docs]
        if len(set(paths)) != len(paths):
            dupes = sorted({p for p in paths if paths.count(p) > 1})
            print(f"{jur}: duplicate citation paths {dupes}", file=sys.stderr)
            return 1
        stem = f"{jur}-snap-manual-completion"
        (ROOT / "manifests" / f"{stem}.yaml").write_text(
            yaml.safe_dump({"version": VERSION, "documents": docs}, sort_keys=False, allow_unicode=True, width=120))
        found = sum(f["found"] for f in info["families"].values())
        taken = sum(f["taken"] for f in info["families"].values())
        summary[jur] = {"documents": len(docs), **info}
        row = rows.get(jur) or {"jurisdiction": jur, "name": NAMES[jur]}
        row.update({
            "name": NAMES[jur], "queue_status": "agent_ready", "source_kind": SOURCE_KIND[jur],
            "primary_source_url": info["index_url"], "target_manifest": f"manifests/{stem}.yaml",
            "target_scope": {"jurisdiction": jur, "document_class": docs[0]["document_class"], "version": VERSION},
            "index_url": info["index_url"], "index_document_count": found, "taken_count": taken,
            "index_families": info["families"],
            "notes": (f"Batch 1 (2026-09-10, #680): {len(docs)} documents taken from the publisher's own index ({found} documents "
                      f"inventoried across {len(info['families'])} families; {taken} taken; citation paths checked against every "
                      f"{jur} provisions file{' in ' + str(corpus_base) if corpus_base else ''}). Extraction proven with the "
                      f"official-documents extractor; see {RUN_NOTE}."),
        })
        rows[jur] = row
        print(f"{jur}: {len(docs)} documents; index families {info['families']}")
    for jur, static in STATIC_ROWS.items():
        row = rows.get(jur) or {"jurisdiction": jur, "name": NAMES[jur]}
        row.update({"name": NAMES[jur], **static})
        rows[jur] = row
    notes = queue.setdefault("policy", {}).setdefault("notes", [])
    if BATCH_NOTE not in notes:
        notes.append(BATCH_NOTE)
    queue["states"] = [rows[j] for j in sorted(rows)]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    QUEUE.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(json.dumps(summary, indent=1))
    print(f"queue {queue['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
