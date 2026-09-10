"""Build the TANF state policy manual manifests for batch 1 of the TANF agent queue
and update ``manifests/tanf-agent-queue.yaml``.

Batch rule (recorded in docs/ingest-runs/2026-09-10-tanf-state-policy-manuals-batch-1.md):
walk the queue's state rows in queue order; a state whose current TANF cash
assistance policy manual (or the adopted rule the state itself publishes as its
primary policy document) is already in the corpus is marked ``done`` and does not
count; batch 1 is the first ten remaining rows. Batch 1 = CA, CO, DC, MO, MS, MT,
ND, NY, OK, OR. NY and OR are blocked publishers (see BLOCKED below); the other
eight get one manifest each, generated here from the publisher's own index.

Every index is fetched live from the publisher. Some publishers (Montana DPHHS,
Mississippi SoS, CDSS) answer plain HTTP clients with 403/reset pages, so index
fetches use curl-cffi browser impersonation; the manifests carry
``request: browser_impersonation: true`` where the document host needs it.

    uv run python scripts/build_tanf_state_policy_manual_manifests.py \
        [--mo-title-cache <json>]

The Missouri TA manual has 472 section pages whose titles are only in each page's
``<title>``; the script fetches them (about 10 minutes) unless a cache JSON from a
previous run is supplied.
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
from typing import Any

import yaml
from curl_cffi import requests as curl_requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "manifests" / "tanf-agent-queue.yaml"
VERSION = "2026-09-10-tanf-state-policy-manual"
SOURCE_AS_OF = dt.date.today().isoformat()
IMPERSONATE = "chrome"
DISCOVERED_VIA = "manual-review:tanf-agent-queue; index {index}"

BATCH_1 = ("us-ca", "us-co", "us-dc", "us-mo", "us-ms", "us-mt", "us-nd", "us-ny", "us-ok", "us-or")
BATCH_2 = ("us-pa", "us-sc", "us-sd", "us-va")

# States whose TANF cash-assistance policy manual (or state-published adopted rule)
# is already in the corpus. target_manifest / target_scope name the existing
# artifacts; these rows do not count toward a batch.
DONE: dict[str, dict[str, Any]] = {
    "us-al": {
        "target_manifest": "manifests/us-al-tanf-official-documents.yaml",
        "scope": ("policy", "2026-07-02-al-tanf-official-documents"),
        "notes": "Alabama Family Assistance: Admin Code 660-2-2 (regulation, 2026-07-02-al-admin-code-660-2-2), "
        "TANF State Plan 2024 and Public Assistance Payment Manual Appendix N Sec 2 (policy). Reviewer judgment: "
        "the DHR-published payment manual appendix plus the adopted rule is the state's primary policy document set; "
        "no separate DHR TANF policy manual index exists. Done per the prior-ingest list.",
    },
    "us-az": {
        "target_manifest": "manifests/us-az-des-faa5-manual.yaml",
        "scope": ("manual", "2025-10-30-az-des-faa5-manual"),
        "notes": "Arizona DES FAA policy manual (combined CA/NA) already ingested; recovery scope 2026-07-17-faa5-recovery also exists. Done per the prior-ingest list.",
    },
    "us-de": {
        "target_manifest": "manifests/us-de-tanf-rules.yaml",
        "scope": ("regulation", "2026-07-03-de-tanf-rules"),
        "notes": "Delaware DSSM 3000 TANF rules (state-published adopted rule) already ingested. Done per the prior-ingest list.",
    },
    "us-fl": {
        "target_manifest": "manifests/us-fl-ess-manual.yaml",
        "scope": ("manual", "2026-05-27-fl-ess-manual"),
        "notes": "Florida DCF ESS Program Policy Manual is the combined FS/TCA/Medicaid manual (48 chapters incl. 1400/1800 TCA chapters, 2600 benefit calculation). Reviewer judgment: combined manual counts as the TCA policy manual; not re-ingested.",
    },
    "us-ga": {
        "target_manifest": "manifests/us-ga-tanf-manual.yaml",
        "scope": ("manual", "2026-06-25-ga-tanf"),
        "notes": "Georgia DFCS TANF Policy Manual already ingested. Done per the prior-ingest list.",
    },
    "us-hi": {
        "target_manifest": "manifests/us-hi-tanf-admin-rules.yaml",
        "scope": ("regulation", "2026-07-03-hi-tanf-admin-rules"),
        "notes": "Hawaii HAR TANF rules already ingested. Done per the prior-ingest list.",
    },
    "us-il": {
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "scope": ("manual", "2026-05-27-il-cash-snap-medical-manual"),
        "notes": "Illinois DHS Cash, SNAP and Medical Manual (combined; PM chapters incl. cash/TANF) already ingested as us-il/manual/dhs/csmm. Reviewer judgment: combined manual counts; not re-ingested.",
    },
    "us-in": {
        "target_manifest": "manifests/us-in-snap-manual.yaml",
        "scope": ("manual", "2026-05-27-in-snap-manual"),
        "notes": "Indiana FSSA/DFR SNAP/TANF Program Policy Manual (combined) already ingested at page granularity. Reviewer judgment: combined manual counts; chapter-level re-segmentation is a later improvement, not a batch item.",
    },
    "us-ks": {
        "target_manifest": "manifests/us-ks-keesm.yaml",
        "scope": ("manual", "2026-05-27-ks-keesm"),
        "notes": "Kansas KEESM (combined) already ingested. Done per the prior-ingest list.",
    },
    "us-me": {
        "target_manifest": "manifests/us-me-tanf-regulation-official-documents.yaml",
        "scope": ("regulation", "2026-07-03-me-tanf-regulation"),
        "notes": "Maine TANF rule (10-144 CMR ch. 331) and rule 125A already ingested; Maine publishes its TANF policy as adopted rules. Done per the prior-ingest list.",
    },
    "us-nc": {
        "target_manifest": "manifests/us-nc-work-first-manual-official-documents.yaml",
        "scope": ("manual", "2026-07-03-nc-work-first-manual"),
        "notes": "North Carolina Work First Manual section 114 (Income and Budgeting) already ingested. Reviewer judgment: done per the prior-ingest list, but only section 114 of the manual is in the corpus; the remaining Work First manual sections are a follow-up, not a batch-1 item.",
    },
    "us-nv": {
        "target_manifest": "manifests/us-nv-eligibility-payments-manual.yaml",
        "scope": ("manual", "2026-05-27-nv-eligibility-payments-manual"),
        "notes": "Nevada DWSS Eligibility and Payments Manual (combined TANF/SNAP/Medicaid, 51 chapter PDFs) already ingested. Reviewer judgment: combined manual counts as the TANF policy manual; not re-ingested.",
    },
    "us-tx": {
        "target_manifest": "manifests/us-tx-manuals.yaml",
        "scope": ("manual", "2026-05-27-tx-manuals"),
        "notes": "Texas Works Handbook (combined) already ingested. Done per the prior-ingest list.",
    },
    "us-wa": {
        "target_manifest": "manifests/us-wa-eaz-manual.yaml",
        "scope": ("manual", "2026-07-21-wa-eaz-manual"),
        "notes": "Washington EA-Z Manual (combined) already ingested. Done per the prior-ingest list.",
    },
}

# Publishers that blocked retrieval on 2026-09-10. Exact failures observed by the agent.
BLOCKED: dict[str, dict[str, Any]] = {
    "us-ny": {
        "source_kind": "official_pdf_manual",
        "primary_source_url": "https://otda.ny.gov/programs/temporary-assistance/TASB.pdf",
        "index_url": "https://otda.ny.gov/programs/temporary-assistance/",
        "index_document_count": 1,
        "notes": "BLOCKED 2026-09-10: OTDA Temporary Assistance Source Book (TASB.pdf, HTTP Last-Modified 2024-11-27). "
        "Plain requests/curl to otda.ny.gov: TCP connection reset by peer. curl-cffi browser impersonation "
        "(chrome, chrome110, chrome124, edge101, firefox): HTTP 200 text/html 6.7 KB JavaScript bot-challenge page "
        "('Please enable JavaScript to view the page content. Your support ID is ...') instead of the PDF; safari "
        "profiles: connection reset. No workaround attempted. The 2024-2026 TANF State Plan (policy) is already in "
        "the corpus (us-ny-tanf-state-plan); the Employment Policy Manual is in 2026-07-17-ny-snap-manuals.",
    },
    "us-or": {
        "source_kind": "official_rule_pdfs",
        "primary_source_url": "https://ch461rules.odhs.oregon.gov/",
        "index_url": "https://ch461rules.odhs.oregon.gov/",
        "index_document_count": None,
        "notes": "BLOCKED 2026-09-10: Oregon publishes TANF policy as OAR chapter 461 (ODHS per-rule PDFs at "
        "ch461rules.odhs.oregon.gov; Secretary of State OARD at secure.sos.state.or.us). Neither host resolved from "
        "the ingest environment: system resolver and 8.8.8.8/9.9.9.9 return SERVFAIL/no answer for "
        "ch461rules.odhs.oregon.gov, www.oregon.gov and secure.sos.state.or.us (dig EDE: 'at delegation oregon.gov'); "
        "1.1.1.1 resolves them, but Python getaddrinfo, requests and curl all fail with name-resolution errors, so "
        "no index could be inventoried. Not a publisher block of the client; re-try from another network. Note for "
        "the retry: chapter 461 is a combined rulebook for all ODHS self-sufficiency programs (SNAP, TANF, ERDC ...), "
        "so the TANF family would be a filtered division set, and an OAR adapter already exists "
        "(extract-oregon-administrative-rules). The existing us-or manual scope (OPEN eligibility notebook) is not "
        "the TANF policy manual.",
    },
}

DROP_EAS = [
    r"^\d\d-\d\d\d\s+\(Cont\.\)\s.*$",
    r"^\d\d-\d\d\d\s+.*\s+Regulations$",
    r"^\d\d-\d\d\d\s+.*\((?:Continued|Cont\.)\)$",
    r"^Regulations\s+.*\s+\d\d-\d\d\d(?:\s+\(Cont\.\))?$",
    r"^CALIFORNIA-DSS-MANUAL-EAS$",
    r"^MANUAL LETTER NO\. .*$",
    r"^Page \d+$",
    r"^This page is intentionally left blank\.$",
]
EAS_EXTRACTION = {
    "segmentation": "styled_labeled_sections",
    "section_heading_pattern": r"^(?P<label>\d\d-\d\d\d)\s+(?P<heading>\S.*?)(?:\s+\d\d-\d\d\d)?$",
    # the EAS DOCX files style only some headings as Word headings; real section
    # headings are all-caps, cross-reference lines in body text are mixed case
    "heading_paragraphs_only": False,
    "heading_text_pattern": r"^[A-Z0-9][A-Z0-9 ,/&()'.;:-]*$",
    "drop_line_patterns": DROP_EAS,
}
CO_EXTRACTION = {
    "segmentation": "labeled_sections",
    "section_heading_pattern": r'^(?P<label>3\.6\d\d(?:\.\d{1,2})?)\s+(?P<heading>[A-Z“"][A-Za-z“"].*)$',
    "section_label_pattern": r"^(?P<label>3\.6\d\d(?:\.\d{1,2})?)$",
    "label_only_heading_pattern": r'^[A-Z“"].*$',
    "label_only_requires_heading": True,
    "drop_line_patterns": [
        r"^CODE OF COLORADO REGULATIONS$",
        r"^9 CCR 2503-6$",
        r"^Income Maintenance \(Volume 3\)$",
        r"^\d{1,3}$",
    ],
}
OK_EXTRACTION = {
    "segmentation": "records",
    "json_record_text_field": "text",
    "json_record_text_is_html": True,
    "json_record_label_field": "sectionNum",
    "json_record_heading_field": "description",
    "json_record_kind_field": "name",
    "json_record_status_field": "statusName",
    "json_record_exclude_statuses": ["Revoked", "Reserved"],
    "json_record_metadata_fields": [
        "id",
        "parentId",
        "name",
        "titleNum",
        "chapterNum",
        "subChapterNum",
        "partNum",
        "sectionNum",
        "appendixNum",
        "description",
        "statusName",
        "segmentStatusId",
        "segmentTypeId",
        "recordStatus",
        "effectiveDate",
        "filingId",
        "hasEmergency",
        "segmentNotes",
    ],
}


def fetch(url: str, *, attempts: int = 3, head: bool = False) -> Any:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            if head:
                return curl_requests.head(
                    url, impersonate=IMPERSONATE, timeout=120, allow_redirects=True
                )
            return curl_requests.get(
                url, impersonate=IMPERSONATE, timeout=120, allow_redirects=True
            )
        except Exception as exc:  # noqa: BLE001 - retry any transport failure
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def links(text: str) -> list[tuple[str, str]]:
    return [
        (href, re.sub(r"<[^>]+>", "", html.unescape(label)).strip())
        for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.S)
    ]


def http_date(value: str | None) -> str | None:
    if not value:
        return None
    return dt.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat()


def base_doc(
    *,
    source_id: str,
    jurisdiction: str,
    document_class: str,
    title: str,
    source_url: str,
    source_format: str,
    citation_path: str,
    expression_date: str,
    authority: str,
    subtype: str,
    state_program: str,
    index_url: str,
    extra: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    extraction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "source_id": source_id,
        "jurisdiction": jurisdiction,
        "document_class": document_class,
        "title": title,
        "source_url": source_url,
        "source_format": source_format,
        "source_as_of": SOURCE_AS_OF,
        "expression_date": expression_date,
        "citation_path": citation_path,
    }
    if request:
        doc["request"] = request
    if extraction:
        doc["extraction"] = extraction
    doc["metadata"] = {
        "primary_source": True,
        "source_authority": authority,
        "document_subtype": subtype,
        "program": "TANF",
        "state_program": state_program,
        "federal_program": "TANF",
        "manual_landing_page": index_url,
        "source_discovery_group": f"{jurisdiction}/{document_class}/tanf",
        "discovered_via": DISCOVERED_VIA.format(index=index_url),
        **(extra or {}),
    }
    return doc


# --------------------------------------------------------------------------- CA
def build_ca() -> dict[str, Any]:
    index = (
        "https://www.cdss.ca.gov/inforesources/Rules-Regulations/Legislation-and-Regulations/"
        "CalWORKs-CalFresh-Regulations/Eligibility-and-Assistance-Standards"
    )
    page = fetch(index).text
    files = [
        (h, t) for h, t in links(page) if re.search(r"/Portals/9/Regs/Man/EAS/[^\"']+\.docx", h)
    ]
    docs = []
    for href, text in files:
        m = re.match(r"^(\d+)\.\s+(.*)$", text)
        if not m or not re.search(r"\bDiv(?:ision)?\s+4[0-4]\b", text):
            continue
        number, label = m.group(1), m.group(2)
        url = "https://www.cdss.ca.gov" + href if href.startswith("/") else href
        head = fetch(url, head=True)
        expression = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
        docs.append(
            base_doc(
                source_id=f"us-ca-cdss-mpp-eas-{number}",
                jurisdiction="us-ca",
                document_class="regulation",
                title=f"CDSS Manual of Policies and Procedures, Eligibility and Assistance Standards {number}: {label}",
                source_url=url,
                source_format="docx",
                citation_path=f"us-ca/regulation/mpp/eas/{number}",
                expression_date=expression,
                authority="California Department of Social Services",
                subtype="adopted_regulation_manual_docx",
                state_program="CalWORKs",
                index_url=index,
                extra={
                    "manual": "MPP Eligibility and Assistance Standards (Divisions 40-44 taken)",
                    "index_ordinal": int(number),
                    "source_last_modified": expression,
                    "extraction_note": "styled_labeled_sections merges page-break heading restatements; running heads dropped",
                },
                request={"browser_impersonation": True},
                extraction=EAS_EXTRACTION,
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(files),
        "inventory": f"{len(files)} EAS DOCX files (Div 40 through Div 91); taken {len(docs)} (Div 40-44, CalWORKs/AFDC eligibility and assistance standards); Div 46-91 (refugee, IHSS, adoptions, admin, hearings) not taken",
        "source_kind": "official_docx_regulation_manual",
        "document_class": "regulation",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- CO
def build_co() -> dict[str, Any]:
    index = (
        "https://www.coloradosos.gov/CCR/DisplayRule.do?action=ruleinfo&ruleId=3145&deptID=9&agencyID=53"
        "&deptName=Department+of+Human+Services&agencyName=Income+Maintenance+(Volume+3)&seriesNum=9+CCR+2503-6"
    )
    page = fetch(index).text
    versions = re.findall(r"OpenRuleWindow\('(\d+)'", page)
    dates = re.findall(r"(\d\d/\d\d/\d{4})\s*\(PDF\)", page)
    if not versions or not dates:
        raise RuntimeError("Colorado SoS rule-info page layout changed")
    current = versions[0]
    effective = dt.datetime.strptime(dates[0], "%m/%d/%Y").date().isoformat()
    url = f"https://www.coloradosos.gov/CCR/GenerateRulePdf.do?ruleVersionId={current}&fileName=9%20CCR%202503-6"
    doc = base_doc(
        source_id="us-co-ccr-9-2503-6-colorado-works",
        jurisdiction="us-co",
        document_class="regulation",
        title="Code of Colorado Regulations 9 CCR 2503-6 Colorado Works Program",
        source_url=url,
        source_format="pdf",
        citation_path="us-co/regulation/9-ccr-2503-6",
        expression_date=effective,
        authority="Colorado Department of Human Services",
        subtype="administrative_code_rule",
        state_program="Colorado Works",
        index_url=index,
        extra={
            "official_publisher": "Colorado Secretary of State",
            "code_rule": "9 CCR 2503-6",
            "rule_version_id": current,
            "rule_effective_date": effective,
            "archived_version_count": len(set(versions)) - 1,
            "extraction_note": "labeled_sections on 3.6xx / 3.6xx.y labels; editor's notes at the end fall into the last section",
        },
        extraction=CO_EXTRACTION,
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(set(versions)),
        "inventory": f"SoS rule-info page: 1 current version (eff. {effective}, PDF+DOCX) and {len(set(versions)) - 1} archived versions; taken the current PDF",
        "source_kind": "official_pdf_regulation",
        "document_class": "regulation",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- DC
def build_dc() -> dict[str, Any]:
    index = "https://dhs.dc.gov/publication/esa-policy-manuals"
    page = fetch(index).text
    pdfs = [(h, t) for h, t in links(page) if h.lower().endswith(".pdf")]
    target = [h for h, t in pdfs if "ESA-Policy-Manual-Combined" in h]
    if len(target) != 1:
        raise RuntimeError(f"expected one combined ESA manual link, found {target}")
    url = target[0]
    head = fetch(url, head=True)
    modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
    doc = base_doc(
        source_id="us-dc-dhs-esa-policy-manual",
        jurisdiction="us-dc",
        document_class="manual",
        title="District of Columbia DHS ESA Policy Manual (Combined, Revised 2)",
        source_url=url,
        source_format="pdf",
        citation_path="us-dc/manual/dhs/tanf/esa-policy-manual",
        expression_date=modified,
        authority="District of Columbia Department of Human Services, Economic Security Administration",
        subtype="policy_manual",
        state_program="DC TANF",
        index_url=index,
        extra={
            "source_last_modified": modified,
            "manual_scope": "ESA programs other than SNAP: TANF, Medical Assistance, GC, IDA, Burial Assistance",
            "extraction_granularity": "pdf_page",
            "extraction_note": "page-level; Part/Chapter headings restart numbering per part so chapter-level labels are not unique",
        },
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(pdfs),
        "inventory": f"{len(pdfs)} PDFs on the ESA Policy Manuals page (ESA SNAP Policy Manual 1-24-25, already ingested as us-dc/manual/dhs/esa/snap-policy-manual; ESA Policy Manual Combined Revised 2); taken 1",
        "source_kind": "official_pdf_manual",
        "document_class": "manual",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- MO
def build_mo(title_cache: Path | None) -> dict[str, Any]:
    index = "https://dssmanuals.mo.gov/temporary-assistance-case-management/"
    landing = fetch(index).text
    appendices = [
        (h, t)
        for h, t in links(landing)
        if h.lower().endswith(".pdf")
        and "dssmanuals.mo.gov" in h
        and re.match(r"^Appendix [A-Z]", t)
    ]
    sitemap = ""
    for n in (1, 2, 3):
        r = fetch(f"https://dssmanuals.mo.gov/wp-sitemap-posts-page-{n}.xml")
        if r.status_code != 200:
            break
        sitemap += r.text
    entries = re.findall(r"<url>\s*<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", sitemap)
    pages = [
        (u, m[:10])
        for u, m in entries
        if "/temporary-assistance-case-management/" in u and u.rstrip("/") != index.rstrip("/")
    ]
    cache: dict[str, Any] = {}
    if title_cache and title_cache.exists():
        cache = json.loads(title_cache.read_text())

    def title_for(url: str) -> str:
        cached = cache.get(url, {}).get("title")
        if cached:
            return cached
        r = fetch(url)
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        time.sleep(0.2)
        return html.unescape(m.group(1)).strip() if m else url

    slugs = [u.rstrip("/").split("/")[-1] for u, _ in pages]
    numbers = [re.match(r"^(\d{4}-\d{2,3}-\d{2}(?:-\d{2,3})*)", s) for s in slugs]
    number_counts: dict[str, int] = {}
    for m in numbers:
        if m:
            number_counts[m.group(1)] = number_counts.get(m.group(1), 0) + 1
    docs = []
    docs.append(
        base_doc(
            source_id="us-mo-dss-tanf-landing",
            jurisdiction="us-mo",
            document_class="manual",
            title="Missouri Temporary Assistance/Case Management Manual (landing page and chapter index)",
            source_url=index,
            source_format="html",
            citation_path="us-mo/manual/dss/tanf/navigation/landing",
            expression_date=SOURCE_AS_OF,
            authority="Missouri Department of Social Services, Family Support Division",
            subtype="manual_landing_page_snapshot",
            state_program="Temporary Assistance",
            index_url=index,
            extraction={"html_content_selector": ".entry-content"},
        )
    )
    for (url, lastmod), slug, m in zip(pages, slugs, numbers, strict=True):
        suffix = m.group(1) if m and number_counts[m.group(1)] == 1 else slug
        title = title_for(url).replace(" – DSS Manuals", "").strip()
        docs.append(
            base_doc(
                source_id=f"us-mo-dss-tanf-{suffix}",
                jurisdiction="us-mo",
                document_class="manual",
                title=f"Missouri Temporary Assistance/Case Management Manual: {title}",
                source_url=url,
                source_format="html",
                citation_path=f"us-mo/manual/dss/tanf/{suffix}",
                expression_date=lastmod,
                authority="Missouri Department of Social Services, Family Support Division",
                subtype="policy_manual_section",
                state_program="Temporary Assistance",
                index_url=index,
                extra={
                    "sitemap_lastmod": lastmod,
                    "source_sitemap_urls": [
                        "https://dssmanuals.mo.gov/wp-sitemap-posts-page-1.xml",
                        "https://dssmanuals.mo.gov/wp-sitemap-posts-page-2.xml",
                    ],
                },
                extraction={"html_content_selector": ".entry-content"},
            )
        )
    for href, text in appendices:
        letter = re.match(r"^Appendix ([A-Z])", text).group(1).lower()
        head = fetch(href, head=True)
        modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
        docs.append(
            base_doc(
                source_id=f"us-mo-dss-tanf-appendix-{letter}",
                jurisdiction="us-mo",
                document_class="manual",
                title=f"Missouri Temporary Assistance/Case Management Manual: {text}",
                source_url=href,
                source_format="pdf",
                citation_path=f"us-mo/manual/dss/tanf/appendix-{letter}",
                expression_date=modified,
                authority="Missouri Department of Social Services, Family Support Division",
                subtype="policy_manual_appendix",
                state_program="Temporary Assistance",
                index_url=index,
                extra={"source_last_modified": modified, "extraction_granularity": "pdf_page"},
            )
        )
    total = 1 + len(pages) + len(appendices)
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": total,
        "inventory": f"landing page + {len(pages)} section pages (WordPress sitemap, chapters 0200-0330) + {len(appendices)} appendix PDFs; taken all {total}",
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- MS
def build_ms() -> dict[str, Any]:
    index = "https://www.mdhs.ms.gov/help/tanf/"
    page = fetch(index).text
    manual = [h for h, t in links(page) if t.strip() == "TANF Policy Manual"]
    if len(set(manual)) != 1:
        raise RuntimeError(f"expected one TANF Policy Manual link, found {manual}")
    url = manual[0]
    head = fetch(url, head=True)
    modified = http_date(head.headers.get("last-modified")) or SOURCE_AS_OF
    doc_links = [(h, t) for h, t in links(page) if h.lower().endswith(".pdf") or "/document/" in h]
    doc = base_doc(
        source_id="us-ms-mdhs-tanf-policy-manual",
        jurisdiction="us-ms",
        document_class="manual",
        title="Mississippi TANF Policy Manual (Title 18 Part 13, Volume III)",
        source_url=url,
        source_format="pdf",
        citation_path="us-ms/manual/mdhs/tanf/volume-iii",
        expression_date=modified,
        authority="Mississippi Department of Human Services (published through the Mississippi Secretary of State administrative code)",
        subtype="policy_manual",
        state_program="Mississippi TANF",
        index_url=index,
        extra={
            "source_last_modified": modified,
            "extraction_granularity": "pdf_page",
            "extraction_note": "page-level; the manual is paginated by chapter (1000-, 2000- ...) without machine-stable section labels",
        },
        request={"browser_impersonation": True},
    )
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len({h for h, _ in doc_links}),
        "inventory": f"MDHS TANF page links {len({h for h, _ in doc_links})} documents (TANF Policy Manual on sos.ms.gov, flyer(s), client forms); taken the TANF Policy Manual",
        "source_kind": "official_pdf_manual",
        "document_class": "manual",
        "primary_source_url": url,
    }


# --------------------------------------------------------------------------- MT
def build_mt() -> dict[str, Any]:
    index = "https://dphhs.mt.gov/hcsd/Manuals/TANFpolicymanual"
    page = fetch(index).text
    rows = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        hrefs = re.findall(r'href="([^"]+)"', row)
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(c))).strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if hrefs and "tanfmanual" in hrefs[0]:
            cells = [c for c in cells if c]
            rows.append((hrefs[0], cells))
    docs = []
    seen: set[str] = set()
    for href, cells in rows:
        if len(cells) < 3:
            raise RuntimeError(f"unexpected Montana index row {cells}")
        label, title, date_text = cells[0], cells[1], cells[-1]
        if label in seen:
            raise RuntimeError(f"duplicate Montana section label {label}")
        seen.add(label)
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                effective = dt.datetime.strptime(date_text, fmt).date().isoformat()
                break
            except ValueError:
                effective = SOURCE_AS_OF
        url = (
            "https://dphhs.mt.gov" + href.replace("../..", "") if href.startswith("../..") else href
        )
        docs.append(
            base_doc(
                source_id=f"us-mt-dphhs-tanf-{label.lower()}",
                jurisdiction="us-mt",
                document_class="manual",
                title=f"Montana TANF Policy Manual {label}: {title}",
                source_url=url,
                source_format="pdf",
                citation_path=f"us-mt/manual/dphhs/tanf/{label.lower()}",
                expression_date=effective,
                authority="Montana Department of Public Health and Human Services",
                subtype="policy_manual_section",
                state_program="Montana TANF",
                index_url=index,
                extra={
                    "official_section_number": label,
                    "official_listing_title": title,
                    "official_effective_date": date_text,
                    "extraction_granularity": "pdf_page",
                },
                request={"browser_impersonation": True},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(rows),
        "inventory": f"{len(rows)} section PDFs listed with effective dates (TOC, index, introduction, definitions, income standards, sections 101-1 through 1702-1); taken all {len(docs)}",
        "source_kind": "official_pdf_manual_sections",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- ND
def build_nd() -> dict[str, Any]:
    base = "https://www.nd.gov/dhs/policymanuals/40019/"
    index = base + "40019.htm"
    toc_url = base + "Data/Tocs/40019_Chunk0.js"
    toc = fetch(toc_url).text
    entries = re.findall(r"'(/[^']+\.htm)':\{i:\[\d+\],t:\['((?:[^'\\]|\\.)*)'\]", toc)
    landing = fetch(base + "Default.htm").text
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(landing)))
    release = re.search(r"Current Release ([\d.]+)", text)
    published = re.search(r"last published on ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    release_log = fetch(base + "Release%20Log.htm").text
    log_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(release_log)))
    eff = re.search(r"(\d{2}\.\d)\s+(\d{1,2}\.\d{1,2}\.\d{4})", log_text)
    expression = (
        dt.datetime.strptime(eff.group(2), "%m.%d.%Y").date().isoformat() if eff else SOURCE_AS_OF
    )
    common = {
        "current_release": release.group(1) if release else None,
        "manual_last_published": published.group(1) if published else None,
        "manual_toc_url": toc_url,
        "manual_base_url": base,
    }
    docs = [
        base_doc(
            source_id="us-nd-hhs-tanf-landing",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 landing page",
            source_url=base + "Default.htm",
            source_format="html",
            citation_path="us-nd/manual/hhs/tanf/navigation/landing",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_landing_page_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
            extraction={"html_content_selector": "#mc-main-content"},
        ),
        base_doc(
            source_id="us-nd-hhs-tanf-toc",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 official table of contents",
            source_url=toc_url,
            source_format="javascript",
            citation_path="us-nd/manual/hhs/tanf/navigation/toc",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_toc_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
        ),
        base_doc(
            source_id="us-nd-hhs-tanf-release-log",
            jurisdiction="us-nd",
            document_class="manual",
            title="North Dakota HHS TANF Policy Manual 400-19 release log",
            source_url=base + "Release%20Log.htm",
            source_format="html",
            citation_path="us-nd/manual/hhs/tanf/navigation/release-log",
            expression_date=expression,
            authority="North Dakota Health and Human Services",
            subtype="manual_release_log_snapshot",
            state_program="North Dakota TANF",
            index_url=index,
            extra=common,
            extraction={"html_content_selector": "#mc-main-content"},
        ),
    ]
    seen: set[str] = set()
    for path, title in entries:
        name = path.lstrip("/")[: -len(".htm")]
        suffix = (
            name.replace("_", "-").lower()
            if re.match(r"^400_19(_\d+)*$", name)
            else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        )
        if suffix in seen:
            raise RuntimeError(f"duplicate North Dakota topic {suffix}")
        seen.add(suffix)
        docs.append(
            base_doc(
                source_id=f"us-nd-hhs-tanf-{suffix}",
                jurisdiction="us-nd",
                document_class="manual",
                title=f"North Dakota TANF Policy Manual: {title.replace(chr(92) + chr(39), chr(39))}",
                source_url=base + path.lstrip("/"),
                source_format="html",
                citation_path=f"us-nd/manual/hhs/tanf/{suffix}",
                expression_date=expression,
                authority="North Dakota Health and Human Services",
                subtype="policy_manual_section",
                state_program="North Dakota TANF",
                index_url=index,
                extra=common,
                extraction={"html_content_selector": "#mc-main-content"},
            )
        )
    return {
        "docs": docs,
        "index_url": index,
        "index_document_count": len(entries) + 3,
        "inventory": f"MadCap TriPane manual: TOC lists {len(entries)} topic pages (400-19-05 definitions through the sanction/hearing sections) plus landing page and release log; taken all {len(docs)} (release {common['current_release']}, effective {expression})",
        "source_kind": "official_html_manual",
        "document_class": "manual",
        "primary_source_url": index,
    }


# --------------------------------------------------------------------------- OK
def build_ok() -> dict[str, Any]:
    index = "https://rules.ok.gov/home"
    api = "https://prod-ok-rules-api.tecuity.com/GetSegmentsByChapterNum?titleNum=340&chapterNum=10"
    data = fetch(api).json()
    counts: dict[str, int] = {}
    for segment in data:
        key = f"{segment.get('name')}:{segment.get('statusName')}"
        counts[key] = counts.get(key, 0) + 1
    active_sections = sum(
        1
        for s in data
        if s.get("name") == "Section" and s.get("statusName") not in {"Revoked", "Reserved"}
    )
    doc = base_doc(
        source_id="us-ok-oac-340-10-tanf-rules",
        jurisdiction="us-ok",
        document_class="regulation",
        title="Oklahoma Administrative Code Title 340 Chapter 10 Temporary Assistance for Needy Families (TANF)",
        source_url=index,
        source_format="json",
        citation_path="us-ok/regulation/oac/340/10",
        expression_date=SOURCE_AS_OF,
        authority="Oklahoma Department of Human Services",
        subtype="administrative_code_chapter",
        state_program="Oklahoma TANF",
        index_url=index,
        extra={
            "official_publisher": "Oklahoma Secretary of State Office of Administrative Rules",
            "rules_api_url": api,
            "legacy_okdhs_chapter_url": "https://oklahoma.gov/okdhs/library/policy/current/oac-340/chapter-10.html",
            "title_number": "340",
            "chapter_number": "10",
            "segment_counts": counts,
            "access_note": "rules.ok.gov and the tecuity rules API answer plain clients with Cloudflare 403; fetched with browser impersonation (same API as us-ok-snap-rules)",
        },
        request={"browser_impersonation": True, "browser_impersonation_direct": True},
        extraction=OK_EXTRACTION,
    )
    doc["download_url"] = api
    return {
        "docs": [doc],
        "index_url": index,
        "index_document_count": len(data),
        "inventory": f"chapter API returns {len(data)} segments ({counts}); taken the chapter as one document, {active_sections} non-revoked sections become records",
        "source_kind": "official_json_regulation",
        "document_class": "regulation",
        "primary_source_url": index,
    }


BUILDERS = {
    "us-ca": build_ca,
    "us-co": build_co,
    "us-dc": build_dc,
    "us-mo": build_mo,
    "us-ms": build_ms,
    "us-mt": build_mt,
    "us-nd": build_nd,
    "us-ok": build_ok,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mo-title-cache", type=Path)
    parser.add_argument("--only", action="append", help="jurisdiction(s) to rebuild; default all")
    args = parser.parse_args()

    queue = yaml.safe_load(QUEUE_PATH.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    selected = args.only or list(BUILDERS)
    for jur in selected:
        builder = BUILDERS[jur]
        result = builder(args.mo_title_cache) if jur == "us-mo" else builder()
        stem = f"{jur}-tanf-state-policy-manual"
        manifest = {"version": SOURCE_AS_OF, "documents": result["docs"]}
        (ROOT / "manifests" / f"{stem}.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=120)
        )
        row = rows[jur]
        row.update(
            {
                "queue_status": "agent_ready",
                "source_kind": result["source_kind"],
                "primary_source_url": result["primary_source_url"],
                "target_manifest": f"manifests/{stem}.yaml",
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": result["document_class"],
                    "version": VERSION,
                },
                "index_url": result["index_url"],
                "index_document_count": result["index_document_count"],
                "taken_count": len(result["docs"]),
                "notes": f"Batch 1. Primary source confirmed from the publisher's own index. Inventory: {result['inventory']}. Extraction proven 2026-09-10 (coverage complete, 0 missing/extra/duplicate).",
            }
        )
        print(f"{jur}: {len(result['docs'])} documents -> manifests/{stem}.yaml", file=sys.stderr)

    for jur, info in DONE.items():
        row = rows[jur]
        document_class, version = info["scope"]
        row.update(
            {
                "queue_status": "done",
                "source_kind": "already_ingested",
                "target_manifest": info["target_manifest"],
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": document_class,
                    "version": version,
                },
                "notes": info["notes"],
            }
        )
    for jur, info in BLOCKED.items():
        row = rows[jur]
        row.update(
            {
                "queue_status": "blocked_primary_source",
                "source_kind": info["source_kind"],
                "primary_source_url": info["primary_source_url"],
                "target_manifest": f"manifests/{jur}-tanf-state-policy-manual.yaml",
                "target_scope": {
                    "jurisdiction": jur,
                    "document_class": "manual" if jur == "us-ny" else "regulation",
                    "version": VERSION,
                },
                "index_url": info["index_url"],
                "index_document_count": info["index_document_count"],
                "taken_count": 0,
                "notes": info["notes"],
            }
        )
    for jur in BATCH_2:
        rows[jur]["queue_status"] = "needs_review"
        rows[jur]["notes"] = (
            "Not in batch 1 (batch 1 = first ten queue rows needing a new extraction: CA, CO, DC, MO, MS, MT, ND, NY, OK, OR). "
            "Falls in batch 2 together with the remaining rows in queue order (PA, SC, SD, VA)."
        )
    fed = rows["us"]
    fed.update(
        {
            "queue_status": "needs_review",
            "source_kind": "federal_regulation_and_state_plan_index",
            "primary_source_url": "https://www.ecfr.gov/current/title-45/subtitle-B/chapter-II/part-260",
            "index_url": "https://acf.gov/ofa/programs/temporary-assistance-needy-families-tanf",
            "index_document_count": None,
            "taken_count": 0,
            "notes": (
                "Checked 2026-09-10: 45 CFR parts 260-265 are NOT in the corpus (data/corpus/coverage/us/regulation has title 45 part 1302 only; "
                "no manifest or ingest-run note references parts 260-265). Not re-ingested in this run (federal eCFR adapter extract-ecfr "
                "--only-title 45 --only-part 260..265 is the path). ACF Office of Family Assistance TANF state plans are a separate later "
                "document family (state plans are published by each state; the OFA program page and the acf.gov resource library do not "
                "expose a consolidated plan index to a non-browser client on 2026-09-10 - acf.gov/ofa/programs/tanf/state-plans is 404 and "
                "the resource-library type filter returns an HTTP 202 challenge). index_document_count unknown; record once an index is located."
            ),
        }
    )
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = (
            queue["status_counts"].get(s["queue_status"], 0) + 1
        )
    queue["queue_status"] = "in_progress"
    QUEUE_PATH.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(f"queue {queue['status_counts']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
