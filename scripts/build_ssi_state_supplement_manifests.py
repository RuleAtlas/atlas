"""Build the state-administered SSI state-supplement manifests (batch 1) from each
publisher's own index, and update the SSI agent queue rows.

Batch 1 covers the ten largest ``needs_review`` states by population (Census Vintage
2024 estimates): TX, FL, NY, IL, OH, NC, VA, WA, MA, CO, with replacements in
population order (MN, SC, AL, ...) for publishers that blocked on the first probe.
Per state the primary document is the state agency's own governing document for the
optional state supplement (agency manual chapter, adopted rule the state itself
publishes, or published payment standard), confirmed from the publisher's index.

States whose supplement rules already live in a corpus scope are recorded as ``done``
with a pointer (``POINTER_ROWS``); publishers that blocked both a plain request and one
browser-impersonation attempt are recorded as ``blocked_primary_source``
(``BLOCKED_ROWS``). The remaining states get one manifest each::

    manifests/us-fl-ssi-state-supplement.yaml   FAC chapter 65A-2 (flrules.org, .doc rule text)
    manifests/us-ma-ssi-state-supplement.yaml   106 CMR 327.000 (mass.gov regulation page + PDF)
    manifests/us-nc-ssi-state-supplement.yaml   State/County Special Assistance manuals (PDF)
    manifests/us-va-ssi-state-supplement.yaml   DARS Auxiliary Grant Program Manual chapters (PDF)

Index pages are cached under ``--cache-dir`` (default ``~/.axiom/ssi-state-supplement-cache``)
so the script can be re-run without re-fetching; the corpus extractor re-fetches every
document itself when it snapshots the source.

    uv run python scripts/build_ssi_state_supplement_manifests.py [--only fl,ma] [--print-index] [--skip-queue]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "manifests" / "ssi-agent-queue.yaml"
VERSION = "2026-09-10-ssi-state-supplement"
SOURCE_AS_OF = "2026-09-10"
USER_AGENT = "axiom-corpus/0.1 (source discovery; https://github.com/TheAxiomFoundation/axiom-corpus)"
DISCOVERED_VIA = "manual-review:ssi-agent-queue batch 1 (state-administered supplements); publisher index"

# Reviewer judgment (2026-09-10): population order for the 29 needs_review rows, Census
# Vintage 2024 estimates (CO 5.96M ranks above MN 5.79M). The first ten are attempted;
# the rest are replacements, taken in order only when a publisher blocks.
POPULATION_ORDER = (
    "TX", "FL", "NY", "IL", "OH", "NC", "VA", "WA", "MA", "CO",
    "MN", "SC", "AL", "LA", "KY", "OR", "OK", "UT", "NE", "NM", "ID", "NH", "ME", "MD", "MO", "WI", "SD", "AK", "WY",
)
BATCH = POPULATION_ORDER[:10]

BUILDERS: dict[str, str] = {}

# Rows resolved by pointer to a scope that already holds the state's supplement rules.
POINTER_ROWS = {
    "TX": {
        "index_families": 'pointer to the 2026-09-10 Medicaid MEPD handbook scope (H-6000, Appendix VIII, Appendix XXXI already taken there): 0 new documents taken; MEPD index chapters A-R, appendices, glossary, forms, revisions, bulletins not re-inventoried',
        "target_manifest": "manifests/us-tx-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-tx", "document_class": "manual",
                         "version": "2026-09-10-medicaid-state-eligibility-manual"},
        "index_url": "https://fhb.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook",
        "notes": (
            "Done by pointer. Texas supplements only institutionalized SSI recipients: HHSC MEPD Handbook H-6000 "
            "'Co-Payment for SSI Cases' (Revision 26-1, effective 2026-03-01) states that HHSC supplements the $30 reduced "
            "SSI payment standard by $45 so recipients keep a $75 personal needs allowance. H-6000, Appendix VIII "
            "(effects of institutionalization on SSI) and Appendix XXXI (budget reference chart) are already in the "
            "2026-09-10 Medicaid eligibility-manual scope as us-tx/manual/hhsc/medicaid/mepd-h-6000, "
            "mepd-appendix-viii and mepd-appendix-xxxi (manifest on branch discovery/ingest-medicaid). The MEPD handbook "
            "index (fhb.hhs.texas.gov, HTTP 200 to a plain client on 2026-09-10; the hhs.texas.gov alias redirects there) "
            "lists chapters A-R plus appendices, glossary, forms, revisions and bulletins; Chapter H lists H-1000 to H-8000."
        ),
    },
    "IL": {
        "index_families": 'pointer to the IDHS Cash, SNAP and Medical Policy Manual / WAG scope (12,450 rows; AABD Cash sections present): 0 new documents taken',
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "target_scope": {"jurisdiction": "us-il", "document_class": "manual",
                         "version": "2026-05-27-il-cash-snap-medical-manual-r2026-07-15-self-contained"},
        "index_url": "https://www.dhs.state.il.us/page.aspx?item=13108",
        "notes": (
            "Done by pointer. Illinois' supplement is AABD Cash (Aid to the Aged, Blind or Disabled), governed by the IDHS "
            "Cash, SNAP and Medical Policy Manual / Workers' Action Guide, which is in the corpus in full (12,450 rows). "
            "AABD sections present include PM I-02-02 (csmm/12262), PM I-03-03 Adult Programs (12286), PM/WAG 11-01-00 AABD "
            "Cash Assistance Standard (15910, 15911), PM/WAG 11-02-03 Using the AABD Cash Assistance Standard (15967, 15968), "
            "WAG 03-03-02 SSI and AABD Cash (13254), WAG 25-03-03 AABD Fuel and Utility Allowances (12668) and PM 22-05-01 "
            "Excess Shelter Allowance (18641); 493 rows mention AABD."
        ),
    },
    "WA": {
        "index_families": 'pointer to WAC chapter 388-474 (4 sections, all in the corpus): 4 found / 0 new documents taken',
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-wa", "document_class": "regulation", "version": "2026-07-01-388-474"},
        "index_url": "https://app.leg.wa.gov/WAC/default.aspx?cite=388-474",
        "notes": (
            "Done by pointer. Washington's SSI State Supplemental Payment is governed by WAC chapter 388-474, which is in the "
            "corpus in full (388-474-0001, -0010, -0012 'What is a state supplemental payment and who can get it?', -0020) as "
            "us-wa/regulation/388/388-474/... from the Legislature's WAC site (adapter scope, no manifest; selected in "
            "manifests/releases/us-rulespec-2026-07-17.json). The DSHS EA-Z manual scope (2026-07-21) carries no SSP page."
        ),
    },
    "CO": {
        "index_families": 'pointer to 9 CCR 2503-5 Adult Financial (92 rows incl. 3.530 OAP and 3.540 AND-SO, all in the corpus): 1 rule found / 0 new documents taken',
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us-co", "document_class": "regulation", "version": "2026-06-19-co-oap-9-ccr-2503-5"},
        "index_url": "https://www.sos.state.co.us/CCR/NumericalCCRDocList.do?deptID=9&agencyID=31",
        "notes": (
            "Done by pointer. Colorado's supplements to SSI are the Old Age Pension (OAP) and Aid to the Needy Disabled - "
            "State Only (AND-SO) programs under the Adult Financial rule 9 CCR 2503-5, already in the corpus in full (92 "
            "rows: 3.500-3.587 incl. 3.530 OAP and 3.540 AND-SO) as us-co/regulation/9-ccr-2503-5/... from the Secretary "
            "of State CCR PDF (adapter scope, no manifest)."
        ),
    },
    "MN": {
        "index_families": 'pointer to the DHS Combined Manual scope (1 PDF, 1,354 rows) and the MSA revised sections 01/2026 scope: 0 new documents taken',
        "target_manifest": "manifests/us-mn-combined-manual.yaml",
        "target_scope": {"jurisdiction": "us-mn", "document_class": "manual",
                         "version": "2026-05-27-mn-combined-manual-r2026-07-15-self-contained"},
        "index_url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=CM_MANUAL",
        "notes": (
            "Done by pointer (replacement 1, after NY blocked). Minnesota Supplemental Aid (MSA) is governed by the DHS "
            "Combined Manual, in the corpus as one PDF (dhs-327301.pdf, 1,354 rows; 523 pages mention MSA, incl. 0020.21 MSA "
            "Assistance Standards), plus the MSA revised sections issued 01/2026 "
            "(us-mn/manual/2026-06-27-mn-dhs-msa-revised-sections-2026-01, mndhs-073585.pdf). mn.gov/dhs answered a Radware "
            "challenge to a plain client on 2026-09-10 (federal run); the corpus copies came from dhs.state.mn.us."
        ),
    },
    "AL": {
        "index_families": 'pointer to Alabama Administrative Code chapter 660-2-4 Optional Supplementation (62 rows, in the corpus): 1 chapter found / 0 new documents taken',
        "target_manifest": "manifests/us-al-admin-code-660-2-4.yaml",
        "target_scope": {"jurisdiction": "us-al", "document_class": "regulation", "version": "2026-06-30-al-admin-code-660-2-4"},
        "index_url": "https://dhr.alabama.gov/",
        "notes": (
            "Done by pointer (replacement 3, after SC blocked). Alabama's optional supplementation rule, Alabama Administrative "
            "Code Chapter 660-2-4 'Optional Supplementation' (DHR), is already in the corpus (62 rows, page granularity) as "
            "us-al/regulation/... from the 2026-06-30 run. dhr.alabama.gov answered HTTP 200 to a plain client on 2026-09-10; "
            "medicaid.alabama.gov did not answer TCP."
        ),
    },
}

# Publishers that blocked a plain request and one browser-impersonation attempt (20 s timeouts).
BLOCKED_ROWS = {
    "NY": (
        "https://otda.ny.gov/programs/ssp/",
        "otda.ny.gov (OTDA State Supplement Program page): plain client TCP connection reset by peer (site root too); "
        "curl-cffi chrome120 impersonation HTTP 200 but a 5,615-byte JavaScript challenge ('Please enable JavaScript to "
        "view the page content. Your support ID is ...') with no page content. No index inventory possible. "
        "SSA regional description remains in the federal family: us/manual/ssa/poms/si/ny01415.026.",
    ),
    "OH": (
        "https://codes.ohio.gov/ohio-administrative-code/chapter-5122-36",
        "Ohio's Residential State Supplement is governed by OAC chapter 5122-36 (Department of Behavioral Health, formerly "
        "OhioMHAS). codes.ohio.gov: connect timeout at 20 s for a plain client and for chrome120 impersonation (same as the "
        "2026-09-10 Medicaid batch). Agency site: mha.ohio.gov redirects to dbh.ohio.gov, which answers HTTP 404 (5,264-byte "
        "error shell) to every plain request and, impersonated, HTTP 200 generic 'Community' pages without the RSS program "
        "text or rule documents; its Rules & Regulations page carries no 5122-36 links. No index inventory possible.",
    ),
    "SC": (
        "https://www.scdhhs.gov/resources/mppm",
        "South Carolina's Optional State Supplementation is administered by SCDHHS (Medicaid Policy and Procedures Manual). "
        "scdhhs.gov answers HTTP 403 (919-byte body) to a plain client for the site root and the MPPM page, and HTTP 403 "
        "(919 bytes) to chrome120 impersonation (replacement 2, after OH blocked). No index inventory possible.",
    ),
}

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "CO": "Colorado", "FL": "Florida", "ID": "Idaho", "IL": "Illinois",
    "KY": "Kentucky", "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MN": "Minnesota",
    "MO": "Missouri", "NC": "North Carolina", "NE": "Nebraska", "NH": "New Hampshire", "NM": "New Mexico",
    "NY": "New York", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "SC": "South Carolina", "SD": "South Dakota",
    "TX": "Texas", "UT": "Utah", "VA": "Virginia", "WA": "Washington", "WI": "Wisconsin", "WY": "Wyoming",
}


def fetch(session: requests.Session, url: str, cache: Path | None, *, pause: float = 0.0) -> str:
    if cache is not None and cache.exists():
        return cache.read_text(encoding="utf-8")
    for attempt in range(4):
        try:
            if pause:
                time.sleep(pause)
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            break
        except requests.RequestException as exc:  # transient: retry with backoff
            if attempt == 3:
                raise
            print(f"retry {attempt + 1} for {url}: {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    text = resp.text
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8")
    return text


def strip_tags(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def us_date(value: str) -> str:
    month, day, year = value.split("/")
    return f"{year}-{int(month):02d}-{int(day):02d}"


def builder(code: str):
    def register(func):
        BUILDERS[code] = func.__name__
        return func

    return register


# ---------------------------------------------------------------- Florida (FAC 65A-2)

FL_INDEX_URL = "https://flrules.org/gateway/ChapterHome.asp?Chapter=65A-2"
FL_RULE_URL = "https://flrules.org/gateway/RuleNo.asp?title={title}&ID={rule}"


@builder("FL")
def build_fl(session: requests.Session, cache_dir: Path) -> tuple[list[dict], dict]:
    """Florida Optional State Supplementation: FAC chapter 65A-2 from the Department of State's
    Florida Administrative Code site (flrules.org), the official publisher of DCF's adopted rules.
    The corpus has FAC 65A-1 (SNAP) as us-fl/regulation/fac/65a-1/<section>; the same convention
    is used here. DCF's own site has no OSS page (guessed paths answered 404)."""
    page = fetch(session, FL_INDEX_URL, cache_dir / "fl" / "chapter-65A-2.html")
    chapter_title = strip_tags(re.search(r"title=([^&\"']+)&", page).group(1)).title()
    rules = []
    for match in re.finditer(r"href=\"/gateway/RuleNo\.asp\?title=([^\"&]+)&ID=(65A-2\.\d+)\"", page):
        rule = match.group(2)
        if rule not in [r[1] for r in rules]:
            rules.append((match.group(1), rule))
    if len(rules) < 5:
        raise SystemExit(f"only {len(rules)} rules parsed from {FL_INDEX_URL}; layout changed?")
    docs = []
    for title_param, rule in rules:
        url = FL_RULE_URL.format(title=quote(title_param), rule=rule)
        body = fetch(session, url, cache_dir / "fl" / f"{rule}.html", pause=1.0)
        text = strip_tags(body)
        rule_title = re.search(r"Rule Title:\s*(.*?)\s*Department", text)
        effective = re.search(r"Effective Date:\s*(\d{1,2}/\d{1,2}/\d{4})", text)
        file_match = re.search(r"readFile\.asp\?sid=0&amp;tid=(\d+)&amp;type=1&amp;file=(65A-2\.\d+\.doc)", body)
        if not (rule_title and effective and file_match):
            raise SystemExit(f"rule page {url} lacks title/effective date/rule text link")
        number = rule.split(".", 1)[1]
        history = re.search(r"History Notes:\s*(.*?)(?:\s*Rule Text|$)", text)
        docs.append(
            {
                "source_id": f"fl-fac-65a-2-{number}",
                "jurisdiction": "us-fl",
                "document_class": "regulation",
                "title": f"Fla. Admin. Code R. {rule}: {rule_title.group(1).strip()}",
                "source_url": url,
                "download_url": f"https://flrules.org/gateway/readFile.asp?sid=0&tid={file_match.group(1)}&type=1&file={file_match.group(2)}",
                "source_format": "doc",
                "source_as_of": SOURCE_AS_OF,
                "expression_date": us_date(effective.group(1)),
                "citation_path": f"us-fl/regulation/fac/65a-2/{number}",
                "extraction": {"heading": f"{rule} {rule_title.group(1).strip()}"},
                "metadata": {
                    "primary_source": True,
                    "source_authority": "Florida Department of Children and Families (rule adopted); Florida Department of State (Florida Administrative Code publisher)",
                    "document_subtype": "agency_regulation_section",
                    "program": "ssi_state_supplement",
                    "state_program": "Optional State Supplementation (OSS)",
                    "federal_program": "SSI",
                    "state": "FL",
                    "manual": "Florida Administrative Code",
                    "title_number": "65",
                    "division": "A",
                    "chapter": "2",
                    "chapter_title": chapter_title,
                    "section": number,
                    "effective_date_printed": us_date(effective.group(1)),
                    "history_notes": history.group(1).strip()[:400] if history else None,
                    "index_url": FL_INDEX_URL,
                    "source_discovery_group": "us-fl/regulation/fac/65a-2",
                    "discovered_via": f"{DISCOVERED_VIA} {FL_INDEX_URL}",
                    "download_note": "the RuleNo page is the publisher's rule record; the rule text is its .doc download (readFile.asp), fetched as download_url",
                },
            }
        )
    for doc in docs:
        doc["metadata"] = {k: v for k, v in doc["metadata"].items() if v is not None}
    index = {
        "index_url": FL_INDEX_URL,
        "index_document_count": len(rules),
        "taken_count": len(docs),
        "families": [{"family": f"FAC chapter 65A-2 {chapter_title} rules", "found": len(rules), "taken": len(docs)}],
    }
    return docs, index


# ---------------------------------------------------------------- Massachusetts (106 CMR 327.000)

MA_INDEX_URL = "https://www.mass.gov/law-library/106-cmr"
MA_PAGE_URL = "https://www.mass.gov/regulations/106-CMR-32700-eligibility-requirements-for-state-supplement-program-ssp"


@builder("MA")
def build_ma(session: requests.Session, cache_dir: Path) -> tuple[list[dict], dict]:
    """Massachusetts State Supplement Program: 106 CMR 327.000 from the mass.gov law library
    (DTA regulations index), regulation page + official PDF. Section-level rows via the
    labeled_sections segmentation (327.010: ... headings), citation us-ma/regulation/106-cmr/327/<label>
    (the TAFDC scope's 106 CMR convention)."""
    index_page = fetch(session, MA_INDEX_URL, cache_dir / "ma" / "106-cmr.html", pause=3.0)
    chapters = sorted(set(re.findall(r"href=\"/regulations/(106-CMR-\d{5}[^\"]*)\"", index_page)))
    if not any(c.startswith("106-CMR-32700") for c in chapters):
        raise SystemExit(f"106 CMR 327.00 not listed on {MA_INDEX_URL}")
    page = fetch(session, MA_PAGE_URL, cache_dir / "ma" / "106-cmr-327.html", pause=3.0)
    title = strip_tags(re.search(r"<title>([^<]*)</title>", page).group(1)).split("|")[0].strip()
    download = re.search(r"href=\"(https://www\.mass\.gov/doc/[^\"]+/download)\"", page)
    if not download:
        raise SystemExit(f"no PDF download link on {MA_PAGE_URL}")
    families = {
        "SSP (327)": [c for c in chapters if c.startswith("106-CMR-327")],
        "Fair hearing rules (343)": [c for c in chapters if c.startswith("106-CMR-343")],
        "SNAP (360-367)": [c for c in chapters if c.startswith("106-CMR-36")],
        "TCAP / TAFDC / EAEDC (701-708)": [c for c in chapters if c.startswith("106-CMR-70")],
    }
    other = [c for c in chapters if not any(c in v for v in families.values())]
    if other:
        families["other"] = other
    doc = {
        "source_id": "ma-dta-106-cmr-327",
        "jurisdiction": "us-ma",
        "document_class": "regulation",
        "title": title,
        "source_url": MA_PAGE_URL,
        "download_url": download.group(1),
        "source_format": "pdf",
        "source_as_of": SOURCE_AS_OF,
        "expression_date": SOURCE_AS_OF,
        "citation_path": "us-ma/regulation/106-cmr/327",
        "extraction": {
            "segmentation": "labeled_sections",
            "start_page": 1,
            # page 1 carries the table of contents (327.010: ... 327.410: ...) followed directly by the
            # body of 327.010; skip lines through the last TOC entry so the TOC does not become sections
            "start_after_pattern": r"^327\.410:\s+Recovery of Overpayments\s*$",
            "section_heading_pattern": r"^(?P<label>327\.\d{3})\s*:\s+(?P<heading>(?!continued\b).+?)\s*$",
            "drop_lines": ["106 CMR: DEPARTMENT OF TRANSITIONAL ASSISTANCE"],
            "drop_line_patterns": [r"^327\.\d{3}\s*:\s*continued\s*$"],
        },
        "metadata": {
            "primary_source": True,
            "source_authority": "Massachusetts Department of Transitional Assistance",
            "document_subtype": "regulation_chapter_pdf",
            "program": "ssi_state_supplement",
            "state_program": "State Supplement Program (SSP)",
            "federal_program": "SSI",
            "state": "MA",
            "cmr_chapter": "106 CMR 327.000",
            "index_url": MA_INDEX_URL,
            "source_discovery_group": "us-ma/regulation/106-cmr/327",
            "discovered_via": f"{DISCOVERED_VIA} {MA_INDEX_URL}",
            "extraction_granularity": "labeled_sections (327.xxx headings); the page-1 table of contents is skipped with start_after_pattern so 327.010-327.110, which begin on page 1, are kept",
            "download_note": "the mass.gov regulation page carries only the official PDF download; the PDF is fetched as download_url",
            "expression_date_note": "fetch date; the PDF's own modification date is 2019-05-06 and the page prints no effective date",
        },
    }
    index = {
        "index_url": MA_INDEX_URL,
        "index_document_count": len(chapters),
        "taken_count": 1,
        "families": [{"family": name, "found": len(items), "taken": 1 if name.startswith("SSP") else 0} for name, items in families.items()],
    }
    return [doc], index


# ---------------------------------------------------------------- North Carolina (Special Assistance)

NC_INDEX_URL = "https://policies.ncdhhs.gov/divisional-n-z/social-services/special-assistance/special-assistance/"
NC_MANUALS = {
    "special-assistance-manual": ("manual", "State/County Special Assistance Manual"),
    "special-assistance-in-home-program-manual": ("in-home-manual", "Special Assistance In-Home Program Manual"),
}


@builder("NC")
def build_nc(session: requests.Session, cache_dir: Path) -> tuple[list[dict], dict]:
    """North Carolina State/County Special Assistance: the DSS Special Assistance Manual and the
    Special Assistance In-Home Program Manual (both revised June 1, 2026) from the NCDHHS
    Policies and Manuals site; PDF page granularity like the 2026-09-10 Medicaid batch."""
    page = fetch(session, NC_INDEX_URL, cache_dir / "nc" / "special-assistance-index.html")
    entries: list[tuple[str, str]] = []
    for slug, label in re.findall(r"href=\"https://policies\.ncdhhs\.gov/document/([^\"/]+)/?\"[^>]*>(.*?)</a>", page, re.S):
        label = strip_tags(label)
        if label and (slug, label) not in entries:
            entries.append((slug, label))
    if len(entries) < 50:
        raise SystemExit(f"only {len(entries)} documents parsed from {NC_INDEX_URL}; layout changed?")

    def family(slug: str, label: str) -> str:
        if slug in NC_MANUALS:
            return "program manuals"
        if re.match(r"CHANGE NO|EFS-SA-CN|SAIH CASE MANAGEMENT MANUAL CHANGE", label, re.I):
            return "change notices"
        if re.search(r"administrative letter", label, re.I):
            return "administrative letters"
        if re.match(r"EIS ", label):
            return "EIS system documents"
        return "forms and notices"

    counts: dict[str, int] = {}
    for slug, label in entries:
        counts[family(slug, label)] = counts.get(family(slug, label), 0) + 1
    docs = []
    for slug, (suffix, title) in NC_MANUALS.items():
        doc_page = fetch(session, f"https://policies.ncdhhs.gov/document/{slug}/", cache_dir / "nc" / f"{slug}.html")
        pdf = re.search(r"href=\"(https://policies\.ncdhhs\.gov/wp-content/uploads/[^\"]+\.pdf)\"", doc_page)
        if not pdf:
            raise SystemExit(f"no PDF link on the {slug} document page")
        revision = re.search(r"Rev-([A-Za-z]+)-(\d{4})\.pdf", pdf.group(1))
        docs.append(
            {
                "source_id": f"nc-dss-{slug}",
                "jurisdiction": "us-nc",
                "document_class": "manual",
                "title": f"NC DSS {title} (revised June 1, 2026)",
                "source_url": f"https://policies.ncdhhs.gov/document/{slug}/",
                "download_url": pdf.group(1),
                "source_format": "pdf",
                "source_as_of": SOURCE_AS_OF,
                "expression_date": "2026-06-01",
                "citation_path": f"us-nc/manual/dss/special-assistance/{suffix}",
                "extraction": {"ocr": True},
                "metadata": {
                    "primary_source": True,
                    "source_authority": "North Carolina Department of Health and Human Services, Division of Social Services",
                    "document_subtype": "program_manual_pdf",
                    "program": "ssi_state_supplement",
                    "state_program": "State/County Special Assistance",
                    "federal_program": "SSI",
                    "state": "NC",
                    "revision_printed": "Revised: June 1, 2026" + (f" (file Rev-{revision.group(1)}-{revision.group(2)})" if revision else ""),
                    "index_url": NC_INDEX_URL,
                    "source_discovery_group": "us-nc/manual/dss/special-assistance",
                    "discovered_via": f"{DISCOVERED_VIA} {NC_INDEX_URL}",
                    "extraction_granularity": "pdf_page",
                    "download_note": "the document page carries only the PDF; the PDF is fetched as download_url",
                },
            }
        )
    index = {
        "index_url": NC_INDEX_URL,
        "index_document_count": len(entries),
        "taken_count": len(docs),
        "families": [{"family": name, "found": count, "taken": len(docs) if name == "program manuals" else 0}
                     for name, count in sorted(counts.items())],
    }
    return docs, index


# ---------------------------------------------------------------- Virginia (Auxiliary Grant)

VA_INDEX_URL = "https://dars.virginia.gov/benefits/auxiliary-grant/for-providers/"
VA_MAIN_URL = "https://dars.virginia.gov/benefits/auxiliary-grant/"
VA_VAC_URL = "https://law.lis.virginia.gov/admincode/title22/agency30/chapter80/"


@builder("VA")
def build_va(session: requests.Session, cache_dir: Path) -> tuple[list[dict], dict]:
    """Virginia Auxiliary Grant Program Manual chapters A-L, listed on the DARS Auxiliary Grant
    'for providers' page and served from the agency's document repository (www.vadsa.org, which
    redirects to www.dsa.virginia.gov, 'Virginia Disability Services Agencies'). PDF page granularity.
    The adopted rule 22VAC30-80 (Virginia LIS) is inventoried as the alternative family, not taken."""
    page = fetch(session, VA_INDEX_URL, cache_dir / "va" / "for-providers.html")
    main = re.search(r"<main.*?</main>", page, re.S)
    body = main.group(0) if main else page
    links: list[tuple[str, str]] = []
    for url, label in re.findall(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", body, re.S):
        label = strip_tags(label)
        if label and not url.startswith(("#", "tel:")) and (url, label) not in links:
            links.append((url, label))
    chapters = [(u, text) for u, text in links if re.match(r"Chapter [A-L] ", text)]
    transmittals = [(u, text) for u, text in links if text.startswith("Manual Transmittal")]
    provider_docs = [
        (u, text) for u, text in links
        if re.search(r"\.(pdf|docx)$", u) and (u, text) not in chapters + transmittals
    ]
    if len(chapters) != 12:
        raise SystemExit(f"expected 12 Auxiliary Grant manual chapters on {VA_INDEX_URL}, found {len(chapters)}")
    vac_page = fetch(session, VA_VAC_URL, cache_dir / "va" / "22vac30-80.html")
    vac_sections = sorted(set(re.findall(r"chapter80/section(\d+)/", vac_page)), key=int)
    docs = []
    for url, label in chapters:
        letter = re.match(r"Chapter ([A-L]) [—-]+ (.+)", label)
        if not letter:
            raise SystemExit(f"unexpected chapter label {label!r}")
        file_id = url.rstrip("/").rsplit("/", 1)[1]
        canonical = f"https://www.dsa.virginia.gov/apps/DocumentRepositoryViewer/fileviewer/{file_id}"
        docs.append(
            {
                "source_id": f"va-dars-auxiliary-grant-manual-chapter-{letter.group(1).lower()}",
                "jurisdiction": "us-va",
                "document_class": "manual",
                "title": f"Virginia DARS Auxiliary Grant Program Manual, Chapter {letter.group(1)}: {letter.group(2).strip()}",
                "source_url": canonical,
                "source_format": "pdf",
                "source_as_of": SOURCE_AS_OF,
                "expression_date": SOURCE_AS_OF,
                "citation_path": f"us-va/manual/dars/auxiliary-grant/chapter-{letter.group(1).lower()}",
                "extraction": {"ocr": True},
                "metadata": {
                    "primary_source": True,
                    "source_authority": "Virginia Department for Aging and Rehabilitative Services",
                    "hosting_authority": "Virginia Disability Services Agencies document repository (www.dsa.virginia.gov; the index links www.vadsa.org, which redirects there)",
                    "document_subtype": "program_manual_chapter_pdf",
                    "program": "ssi_state_supplement",
                    "state_program": "Auxiliary Grant (AG)",
                    "federal_program": "SSI",
                    "state": "VA",
                    "manual_chapter": letter.group(1),
                    "index_link_url": url,
                    "index_url": VA_INDEX_URL,
                    "program_page_url": VA_MAIN_URL,
                    "regulation_alternative": f"{VA_VAC_URL} (22VAC30-80, {len(vac_sections)} sections incl. FORMS; not taken)",
                    "source_discovery_group": "us-va/manual/dars/auxiliary-grant",
                    "discovered_via": f"{DISCOVERED_VIA} {VA_INDEX_URL}",
                    "extraction_granularity": "pdf_page",
                    "expression_date_note": "fetch date; each chapter prints its own revision month (e.g. Chapter D 11/18) on the cover",
                },
            }
        )
    index = {
        "index_url": VA_INDEX_URL,
        "index_document_count": len(chapters) + len(transmittals) + len(provider_docs),
        "taken_count": len(docs),
        "families": [
            {"family": "Auxiliary Grant Program Manual chapters", "found": len(chapters), "taken": len(docs)},
            {"family": "manual transmittals", "found": len(transmittals), "taken": 0},
            {"family": "provider manuals, agreements, certification and forms", "found": len(provider_docs), "taken": 0},
            {"family": f"22VAC30-80 Auxiliary Grants Program sections on Virginia LIS ({VA_VAC_URL}; separate index)",
             "found": len(vac_sections), "taken": 0},
        ],
    }
    return docs, index


# ---------------------------------------------------------------- queue

def manifest_path(code: str) -> Path:
    return ROOT / "manifests" / f"us-{code.lower()}-ssi-state-supplement.yaml"


def update_queue(results: dict[str, dict]) -> dict:
    queue = yaml.safe_load(QUEUE.read_text())
    rows = {row["jurisdiction"]: row for row in queue["states"]}
    for code, index in results.items():
        row = rows[f"us-{code.lower()}"]
        docs = index["docs"]
        families = "; ".join(f"{f['family']}: {f['found']} found / {f['taken']} taken" for f in index["families"])
        row.update(
            {
                "queue_status": "agent_ready",
                "source_kind": index["source_kind"],
                "primary_source_url": docs[0]["source_url"],
                "target_manifest": str(manifest_path(code).relative_to(ROOT)),
                "target_scope": {"jurisdiction": f"us-{code.lower()}", "document_class": docs[0]["document_class"], "version": VERSION},
                "index_url": index["index_url"],
                "index_document_count": index["index_document_count"],
                "taken_count": index["taken_count"],
                "index_families": families,
                "notes": index["note"],
            }
        )
    for code, pointer in POINTER_ROWS.items():
        row = rows[f"us-{code.lower()}"]
        row.update(
            {
                "queue_status": "done",
                "source_kind": "official_state_or_ssa_document",
                "primary_source_url": None,
                "target_manifest": pointer["target_manifest"],
                "target_scope": pointer["target_scope"],
                "index_url": pointer["index_url"],
                "index_document_count": None,
                "taken_count": 0,
                "index_families": pointer["index_families"],
                "notes": pointer["notes"] + " (2026-09-10 state-supplement batch 1.)",
            }
        )
    for code, (url, note) in BLOCKED_ROWS.items():
        row = rows[f"us-{code.lower()}"]
        row.update(
            {
                "queue_status": "blocked_primary_source",
                "source_kind": "state_agency_document",
                "primary_source_url": url,
                "target_manifest": None,
                "index_url": url,
                "index_document_count": None,
                "taken_count": 0,
                "index_families": "no index inventory possible (publisher blocked; see notes)",
                "notes": f"Blocked 2026-09-10 (state-supplement batch 1): {note}",
            }
        )
    queue["status_counts"] = {}
    for row in queue["states"]:
        queue["status_counts"][row["queue_status"]] = queue["status_counts"].get(row["queue_status"], 0) + 1
    note = (
        "2026-09-10 SSI state-supplement batch 1: scripts/build_ssi_state_supplement_manifests.py; ten largest "
        "needs_review states by population attempted (TX, FL, NY, IL, OH, NC, VA, WA, MA, CO) with replacements MN, SC, AL; "
        "docs/ingest-runs/2026-09-10-ssi-state-supplements-batch-1.md."
    )
    notes = queue.setdefault("policy", {}).setdefault("notes", [])
    if note not in notes:
        notes.append(note)
    QUEUE.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    return queue["status_counts"]


SOURCE_KINDS = {
    "FL": "official_state_regulation",
    "MA": "official_state_regulation",
    "NC": "official_state_agency_manual",
    "VA": "official_state_agency_manual",
}
ROW_NOTES = {
    "FL": (
        "Optional State Supplementation (OSS): FAC chapter 65A-2 (8 rules, each rule's .doc text from flrules.org, the "
        "Department of State's FAC publisher; rule pages print the effective dates 2001-12-16 to 2025-06-24). DCF's own "
        "site has no OSS page (guessed paths 404) and the ESS Program Policy Manual scope carries no OSS text. "
        "document_class regulation, citation us-fl/regulation/fac/65a-2/<section> (the FAC 65A-1 convention)."
    ),
    "MA": (
        "State Supplement Program (SSP): 106 CMR 327.000 Eligibility Requirements for SSP (DTA), one regulation PDF from the "
        "mass.gov law library 106 CMR index (18 chapters listed; 327 taken), 24 section rows 327.010-327.410 (the TOC misprints 327.160 as 322.160). document_class "
        "regulation, citation us-ma/regulation/106-cmr/327/<section>. mass.gov answered HTTP 200 to a paced plain client "
        "on 2026-09-10 (the guessed law-library/106-cmr-327 path is 404; the regulation page is /regulations/106-CMR-32700-...)."
    ),
    "NC": (
        "State/County Special Assistance (SA, adult care home) and SA In-Home: the two DSS program manuals (PDF, revised "
        "2026-06-01; 368 and 48 pages) from the NCDHHS Policies and Manuals Special Assistance index, which also lists "
        "change notices, administrative letters, forms and EIS documents (not taken). document_class manual, citation "
        "us-nc/manual/dss/special-assistance/{manual,in-home-manual}, page granularity."
    ),
    "VA": (
        "Auxiliary Grant (AG): DARS Auxiliary Grant Program Manual chapters A-L (12 PDFs) listed on the DARS AG 'for "
        "providers' page and served by the agency repository www.dsa.virginia.gov (linked as www.vadsa.org). Manual "
        "transmittal DARS-APSD-18 and provider documents not taken; the adopted rule 22VAC30-80 (Virginia LIS, 12 sections) "
        "is the alternative family, not taken. document_class manual, citation us-va/manual/dars/auxiliary-grant/chapter-<x>, "
        "page granularity."
    ),
}


def index_markdown(code: str, index: dict) -> str:
    lines = [f"**us-{code.lower()}** — {index['index_url']}", "", "| Family | Found | Taken |", "| --- | ---: | ---: |"]
    for fam in index["families"]:
        lines.append(f"| {fam['family']} | {fam['found']} | {fam['taken']} |")
    lines.append(f"| **Total on index** | {index['index_document_count']} | {index['taken_count']} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", type=Path, default=Path.home() / ".axiom" / "ssi-state-supplement-cache")
    parser.add_argument("--only", help="comma-separated state codes to build (default: all extractable states)")
    parser.add_argument("--print-index", action="store_true", help="print each publisher index inventory as markdown")
    parser.add_argument("--skip-queue", action="store_true", help="do not rewrite manifests/ssi-agent-queue.yaml")
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    codes = [c.strip().upper() for c in args.only.split(",")] if args.only else list(BUILDERS)
    results: dict[str, dict] = {}
    for code in codes:
        build = globals()[BUILDERS[code]]
        docs, index = build(session, args.cache_dir)
        paths = [d["citation_path"] for d in docs]
        if len(set(paths)) != len(paths):
            raise SystemExit(f"duplicate citation paths in {code} manifest")
        manifest_path(code).write_text(
            yaml.safe_dump({"version": VERSION, "documents": docs}, sort_keys=False, allow_unicode=True, width=120)
        )
        index.update({"docs": docs, "source_kind": SOURCE_KINDS[code], "note": ROW_NOTES[code]})
        results[code] = index
        if args.print_index:
            print(index_markdown(code, index), "\n")
        print(
            json.dumps(
                {
                    "state": code,
                    "manifest": str(manifest_path(code).relative_to(ROOT)),
                    "index_document_count": index["index_document_count"],
                    "taken_count": index["taken_count"],
                    "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                }
            )
        )
    if not args.skip_queue:
        print("queue status_counts:", update_queue(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
