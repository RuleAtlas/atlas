"""Build the corpus manifest for CMS Pub 100-01, Medicare General Information,
Eligibility, and Entitlement Manual (every chapter PDF), inventory the CMS
Internet-Only Manuals (IOM) index, and update the Medicare agent queue.

Primary official source: the CMS IOM index,
https://www.cms.gov/medicare/regulations-guidance/manuals/internet-only-manuals-ioms
(Centers for Medicare & Medicaid Services). The index lists one page per
publication; the Pub 100-01 page lists one PDF per chapter. Each chapter PDF
opens with a table of contents whose header prints the chapter's latest
transmittal ("(Rev. 12425; Issued: 12-21-23)"); that issued date becomes the
chapter's expression_date. The body repeats every section heading in bold
("10.1 - Inpatient Hospital Deductible"), so extraction uses labeled_sections
with section_heading_requires_bold and a per-chapter start_after_pattern
anchored on the last table-of-contents line.

cms.gov serves both HTML and PDF to the corpus user agent over a complete TLS
chain; no certificate bundle or browser impersonation is needed.

    uv run python scripts/build_cms_iom_100_01_manifests.py \
        [--download-dir ~/.axiom/cache/cms-iom-100-01]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF, an axiom-corpus dependency
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.cms.gov"
INDEX = f"{BASE}/medicare/regulations-guidance/manuals/internet-only-manuals-ioms"
PAPER_INDEX = f"{BASE}/medicare/regulations-guidance/manuals/paper-based-manuals"
PUBLICATION = "100-01"
VERSION = "2026-09-10-medicare-cms-iom-100-01"
SOURCE_AS_OF = "2026-09-10"
FALLBACK_EXPRESSION_DATE = SOURCE_AS_OF
USER_AGENT = "axiom-corpus/0.1 (source discovery)"
# site-wide footer link present on every cms.gov page; not a manual document
SITE_WIDE_LINKS = ("/files/document/agent/broker-help-desks.pdf",)

# "10 - Title", "10.1 - Title", "30.30.1.1 - Title"; a spaced dash keeps
# "10-foot", "1-800-MEDICARE", "100-01 - General Information" and "1966 - 1972"
# out. The bold requirement in the extraction config removes the remaining
# in-text references such as "40.2 - Shared System Maintainer" in an exhibit.
SECTION_HEADING_PATTERN = r"^(?P<label>\d+(?:\.\d+)*)\s+[-–—]\s*(?P<heading>[A-Za-z(].*)$"
# A wrapped heading continues on the next line in Title Case ("Payer (D-SEP)",
# "or After October 1, 1983 Under PPS", "(Contractors)", "Services - General",
# "... Services - A Brief Description"). The transmittal line
# that follows every heading ("(Rev. 1, 09-11-02)", "(Rev .11764; ...)",
# "(Rev.: 128, ...)") and bold sub-captions ("A. General", "NOTE:", "POLICY")
# are excluded so they stay in the section body, and a line shaped like the
# next section heading ("10.1 - Inpatient Hospital Deductible" after a bare
# container heading with no transmittal line) is never absorbed.
_JOIN = (
    "(?:a|an|and|as|at|by|for|from|in|of|on|or|the|to|under|with|is|are|now|than|that|"
    "who|whom|which|when|where|not|yet|available)"
)
_WORD = rf"(?:\(?[A-Z0-9][^\s]*|[-–—]|{_JOIN}\b[^\s]*)"
HEADING_CONTINUATION_PATTERN = (
    rf"^(?P<heading>(?!\(Rev\b)(?!\d+(?:\.\d+)*\s+[-–—])(?![A-Z][.)\-–]\s)(?!NOTE\b)(?![A-Z]+:?$)(?![A-Z][A-Z ]+$)"
    rf"{_WORD}(?:\s+{_WORD})*)$"
)
HEADING_RE = re.compile(SECTION_HEADING_PATTERN)
REV_RE = re.compile(
    r"\(Rev\.?\s*:?\s*(?P<rev>\d+)\s*[;,]\s*(?:Issued:?\s*)?(?P<date>\d{1,2}-\d{1,2}-\d{2,4})"
)
CHAPTER_LINK_RE = re.compile(r"^Chapter\s*(?P<number>\d+)\s*[-–—]+\s*(?P<title>\S.*)$", re.I)


def fetch(session: requests.Session, url: str) -> requests.Response:
    resp = session.get(url, timeout=120)
    resp.raise_for_status()
    return resp


def links(page: str) -> list[tuple[str, str]]:
    out = []
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(text))).strip()
        out.append((href if href.startswith("http") else BASE + href, text))
    return out


def index_rows(page: str) -> list[dict[str, str]]:
    """Publication rows of a CMS manuals index table: number, title, page URL."""
    rows = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(cell))).strip()
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        ]
        hrefs = re.findall(r'href="([^"]+)"', row)
        if len(cells) < 2 or not hrefs:
            continue
        number = re.sub(r"^Publication #\s*", "", cells[0]).strip()
        title = re.sub(r"^Title\s*", "", cells[1]).strip()
        if not re.match(r"^\d", number):
            continue
        href = hrefs[0]
        rows.append({"publication": number, "title": title, "url": href if href.startswith("http") else BASE + href})
    return rows


def publication_documents(page: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (chapter links, other download links) on one publication page."""
    chapters, other = [], []
    for href, text in links(page):
        path = href.removeprefix(BASE)
        is_download = "/manuals/downloads/" in path.lower() or path.lower().endswith((".pdf", ".zip"))
        if not is_download or path in SITE_WIDE_LINKS:
            continue
        (chapters if CHAPTER_LINK_RE.match(text) else other).append((href, text))
    return chapters, other


def normalized_lines(document: fitz.Document) -> list[tuple[str, int]]:
    """Text lines the same way the official-documents extractor sees them."""
    out = []
    for page_index, page in enumerate(document, start=1):
        for raw in page.get_text("text").splitlines():
            line = " ".join(raw.split())
            if line and not re.match(r"^Page \d+$", line):
                out.append((line, page_index))
    return out


def chapter_facts(pdf_path: Path) -> dict[str, Any]:
    """Latest TOC transmittal, last TOC line, and page count of one chapter PDF."""
    with fitz.open(pdf_path) as document:
        page_count = len(document)
        lines = normalized_lines(document)
    # The TOC header (before "Transmittals for Chapter N") prints the chapter's
    # latest transmittal; chapter 6 prints two, so take the latest issued date.
    header_end = next(
        (i for i, (line, _) in enumerate(lines) if re.match(r"^Transmittals for Chapter", line)),
        None,
    )
    if header_end is None:
        raise RuntimeError(f"{pdf_path.name}: no 'Transmittals for Chapter' line in the TOC header")
    transmittals = []
    for line, _ in lines[:header_end]:
        for match in REV_RE.finditer(line):
            month, day, year = match.group("date").split("-")
            year_full = int(year) if len(year) == 4 else 2000 + int(year)
            transmittals.append((dt.date(year_full, int(month), int(day)), int(match.group("rev")), line))
    # The body starts where the first TOC heading label reappears; the line
    # before that is the last TOC line, the start_after anchor.
    seen: dict[str, int] = {}
    body_start = None
    for i, (line, _) in enumerate(lines):
        match = HEADING_RE.match(line)
        if match is None:
            continue
        if match.group("label") in seen:
            body_start = i
            break
        seen[match.group("label")] = i
    if body_start is None:
        raise RuntimeError(f"{pdf_path.name}: could not find where the body restarts after the TOC")
    last_toc_line = lines[body_start - 1][0]
    earlier = sum(1 for line, _ in lines[:body_start - 1] if line == last_toc_line)
    if earlier:
        raise RuntimeError(f"{pdf_path.name}: last TOC line {last_toc_line!r} also appears earlier")
    return {
        "page_count": page_count,
        "toc_section_count": len(seen),
        "body_start_page": lines[body_start][1],
        "last_toc_line": last_toc_line,
        "transmittals": sorted(transmittals),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path.home() / ".axiom" / "cache" / "cms-iom-100-01",
        help="where chapter PDFs are cached while computing per-chapter extraction settings",
    )
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1. The publisher's own index: every publication, with chapter counts.
    publications = index_rows(fetch(session, INDEX).text)
    if len(publications) < 20:
        print(f"only {len(publications)} publications on the IOM index; layout changed?", file=sys.stderr)
        return 1
    inventory = []
    taken_row = None
    for row in publications:
        chapters, other = publication_documents(fetch(session, row["url"]).text)
        crosswalks = [text for _href, text in other if re.match(r"^Chapter \d+ Crosswalk$", text)]
        other_documents = [text for _href, text in other if text not in crosswalks]
        if crosswalks:
            other_documents.append(f"{len(crosswalks)} per-chapter crosswalks")
        entry = {
            **row,
            "chapter_count": len(chapters),
            "other_document_count": len(other),
            "other_documents": other_documents,
            "taken": row["publication"] == PUBLICATION,
        }
        inventory.append(entry)
        if entry["taken"]:
            taken_row = (row, chapters, other)
    if taken_row is None:
        print(f"Pub {PUBLICATION} is not on the IOM index", file=sys.stderr)
        return 1
    paper_rows = index_rows(fetch(session, PAPER_INDEX).text)
    paper_inventory = []
    for row in paper_rows:
        chapters, other = publication_documents(fetch(session, row["url"]).text)
        paper_inventory.append(
            {**row, "chapter_count": len(chapters), "other_document_count": len(other), "taken": False}
        )

    # 2. Pub 100-01: one document per chapter PDF.
    pub_row, chapter_links, other_links = taken_row
    args.download_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    for href, text in chapter_links:
        match = CHAPTER_LINK_RE.match(text)
        assert match is not None
        number = int(match.group("number"))
        chapter_title = match.group("title").strip()
        pdf_path = args.download_dir / href.rsplit("/", 1)[-1]
        last_modified = None
        if not pdf_path.exists():
            resp = fetch(session, href)
            pdf_path.write_bytes(resp.content)
            last_modified = resp.headers.get("Last-Modified")
        else:
            # cms.gov does not answer HEAD with Last-Modified; open a streamed GET
            # and close it without reading the body.
            with session.get(href, timeout=60, stream=True) as resp:
                last_modified = resp.headers.get("Last-Modified") if resp.ok else None
        facts = chapter_facts(pdf_path)
        if facts["transmittals"]:
            issued, rev, rev_line = facts["transmittals"][-1]
            expression_date = issued.isoformat()
            expression_source = f"TOC header transmittal line {rev_line!r}"
            latest_transmittal = f"Rev. {rev}, issued {issued.isoformat()}"
        else:
            expression_date = FALLBACK_EXPRESSION_DATE
            expression_source = "no transmittal date printed in the TOC header; source_as_of used"
            latest_transmittal = None
        metadata = {
            "primary_source": True,
            "source_authority": "Centers for Medicare & Medicaid Services",
            "document_subtype": "internet_only_manual_chapter",
            "program": "MEDICARE",
            "publication": PUBLICATION,
            "publication_title": pub_row["title"],
            "publication_page": pub_row["url"],
            "chapter": number,
            "chapter_title": chapter_title,
            "latest_transmittal": latest_transmittal,
            "expression_date_source": expression_source,
            "pdf_page_count": facts["page_count"],
            "toc_section_count": facts["toc_section_count"],
            "extraction_granularity": "numbered_section",
            "source_discovery_group": "us/manual/cms-iom-100-01",
            "discovered_via": f"manual-review:medicare-agent-queue; index {INDEX}; publication page {pub_row['url']}",
        }
        if last_modified:
            metadata["http_last_modified"] = last_modified
        documents.append(
            {
                "source_id": f"us-cms-iom-{PUBLICATION}-chapter-{number}",
                "jurisdiction": "us",
                "document_class": "manual",
                "title": f"CMS Pub {PUBLICATION} {pub_row['title']}, Chapter {number} - {chapter_title}",
                "source_url": href,
                "source_format": "pdf",
                "source_as_of": SOURCE_AS_OF,
                "expression_date": expression_date,
                "citation_path": f"us/manual/cms/iom/{PUBLICATION}/chapter-{number}",
                "extraction": {
                    "segmentation": "labeled_sections",
                    "section_heading_pattern": SECTION_HEADING_PATTERN,
                    "section_heading_requires_bold": True,
                    "heading_continuation_pattern": HEADING_CONTINUATION_PATTERN,
                    # skip the table of contents, which repeats every heading
                    "start_after_pattern": "^" + re.escape(facts["last_toc_line"]) + "$",
                },
                "metadata": metadata,
            }
        )
    documents.sort(key=lambda doc: doc["metadata"]["chapter"])
    manifest_path = ROOT / "manifests" / f"us-cms-iom-{PUBLICATION}.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"version": VERSION, "documents": documents}, sort_keys=False, allow_unicode=True, width=120)
    )

    # 3. Queue: the single federal row.
    queue_path = ROOT / "manifests" / "medicare-agent-queue.yaml"
    queue = yaml.safe_load(queue_path.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    row = rows["us"]
    row.update(
        {
            "queue_status": "agent_ready",
            "source_kind": "official_pdf_manual_chapters",
            "primary_source_url": pub_row["url"],
            "target_manifest": f"manifests/{manifest_path.name}",
            "target_scope": {"jurisdiction": "us", "document_class": "manual", "version": VERSION},
            "index_url": INDEX,
            "index_document_count": len(publications),
            "taken_count": 1,
            "publication_page": {
                "url": pub_row["url"],
                "document_count": len(chapter_links) + len(other_links),
                "chapter_count": len(chapter_links),
                "chapters_taken": len(documents),
                "not_taken": [text for _href, text in other_links],
            },
            "index_inventory": inventory,
            "paper_based_manuals": {"index_url": PAPER_INDEX, "publications": paper_inventory},
            "notes": (
                f"Family: CMS Internet-Only Manuals. Pub {PUBLICATION} ({pub_row['title']}) taken in full: "
                f"{len(documents)} chapter PDFs from the publication page listed on the IOM index; the Crosswalks "
                "PDF on the same page is a finding aid, not a chapter, and is not taken. The existing "
                "us/guidance/cms/original-medicare-part-a-b scope is not re-ingested. Pub 100-02 (Benefit Policy), "
                "Pub 100-04 (Claims Processing) and Pub 45 (State Medicaid Manual) are candidate later families; "
                "cms.gov fact sheets, medicare.gov pages, SSA POMS and state pages on the lead list are not CMS "
                "manuals and stay out of this family."
            ),
        }
    )
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    queue_path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(
        f"wrote {manifest_path.relative_to(ROOT)} with {len(documents)} chapters; "
        f"IOM index publications {len(publications)}, paper-based {len(paper_inventory)}; "
        f"queue {queue['status_counts']}"
    )
    for doc in documents:
        meta = doc["metadata"]
        print(
            f"  chapter {meta['chapter']}: {meta['toc_section_count']} TOC sections, "
            f"{meta['pdf_page_count']} pages, expression {doc['expression_date']} ({meta['latest_transmittal']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
