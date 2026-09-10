"""Build one official-document manifest per state for the state Medicaid eligibility
policy manuals (batch 1 of `manifests/medicaid-agent-queue.yaml`) and update the queue.

Every document is confirmed from the state Medicaid agency's own index page, fetched
live here so the manifest reflects what the publisher lists today. The lead-list
PolicyEngine citations in the queue are discovery only and are never used as sources.

Batch 1 = the two queued state rows (AR, VA) + the eight largest states by population
(CA, TX, FL, NY, PA, IL, OH, GA). Where a state's Medicaid eligibility chapters are
already in the corpus under a combined manual (FL, IL) the row is marked `done` with a
pointer and the next largest state is pulled (NC for IL; MI for FL, which is itself
already covered by the Bridges manual, so NJ is pulled). CA and OH block retrieval and
are recorded as `blocked_primary_source` with the exact failure.

    uv run python scripts/build_medicaid_state_eligibility_manual_manifests.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "manifests" / "medicaid-agent-queue.yaml"
VERSION = "2026-09-10-medicaid-state-eligibility-manual"
SOURCE_AS_OF = dt.date.today().isoformat()
EXPRESSION_DATE = SOURCE_AS_OF  # current-effective manual trees; see run note
UA = "Axiom/1.0 (Legal Archive; contact@axiom-foundation.org) https://github.com/TheAxiomFoundation/axiom-corpus"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DISCOVERED_VIA = "manual-review:medicaid-agent-queue batch 1; publisher index {index}"

_LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


def fetch(url: str, *, browser: bool = False) -> str:
    """GET with TLS verification on; retry only transient connection errors (e.g. a resolver blip)."""
    for attempt in range(4):
        try:
            resp = requests.get(url, headers={"User-Agent": BROWSER_UA if browser else UA}, timeout=90)
            resp.raise_for_status()
            return resp.text
        except requests.ConnectionError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


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


def slug(value: str, limit: int = 80) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:limit].strip("-")


def document(
    jur: str,
    *,
    label: str,
    title: str,
    url: str,
    fmt: str,
    authority: str,
    manual: str,
    index_url: str,
    subtype: str,
    extraction: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "source_id": f"{jur}-medicaid-{label.replace('/', '-')}",
        "jurisdiction": jur,
        "document_class": "manual",
        "title": title,
        "source_url": url,
        "source_format": fmt,
        "source_as_of": SOURCE_AS_OF,
        "expression_date": EXPRESSION_DATE,
        "citation_path": f"{jur}/manual/{extra.pop('agency') if extra and 'agency' in extra else 'x'}/medicaid/{label}",
    }
    if request:
        doc["request"] = request
    if extraction:
        doc["extraction"] = extraction
    doc["metadata"] = {
        "primary_source": True,
        "source_authority": authority,
        "document_subtype": subtype,
        "program": "MEDICAID",
        "manual": manual,
        "manual_index_url": index_url,
        "source_discovery_group": f"{jur}/manual/medicaid",
        "discovered_via": DISCOVERED_VIA.format(index=index_url),
        **(extra or {}),
    }
    return doc


# --------------------------------------------------------------------------- states


def build_va() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.dmas.virginia.gov/for-applicants/eligibility-guidance/eligibility-manual/"
    page = fetch(index)
    docs = []
    families: dict[str, dict[str, int]] = {"manual_chapter_pdf": {"found": 0, "taken": 0}, "other_pdf": {"found": 0, "taken": 0}}
    for href, text in links(page, index):
        if not href.lower().endswith(".pdf"):
            continue
        m = re.match(r"^Chapter (M\d{2}) - (.+)$", text)
        if m:
            code, heading = m.group(1).lower(), m.group(2)
            label = code if code != "m00" else f"{code}-{slug(heading)}"
            title = f"Virginia Medical Assistance Eligibility Manual: Chapter {m.group(1)} {heading}"
        elif text == "Table of Contents":
            label, title = "m000-table-of-contents", "Virginia Medical Assistance Eligibility Manual: Table of Contents"
        else:
            families["other_pdf"]["found"] += 1
            continue
        families["manual_chapter_pdf"]["found"] += 1
        families["manual_chapter_pdf"]["taken"] += 1
        docs.append(document("us-va", label=label, title=title, url=href, fmt="pdf",
                             authority="Virginia Department of Medical Assistance Services",
                             manual="Virginia Medical Assistance Eligibility Manual", index_url=index,
                             subtype="eligibility_manual_chapter_pdf", extraction={"ocr": True},
                             extra={"agency": "dmas", "extraction_granularity": "pdf_page"}))
    return docs, {"index_url": index, "families": families}


def build_ny() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.health.ny.gov/health_care/medicaid/reference/mrg/"
    page = fetch(index, browser=True)
    chapters = {
        "mrg-intro.pdf": ("introduction", "Introduction to the Medicaid Reference Guide and Instructions for Use"),
        "glossary.pdf": ("glossary", "Glossary"),
        "category.pdf": ("categorical-factors", "Categorical Factors"),
        "income.pdf": ("income", "Income"),
        "resindex.pdf": ("resources", "Resources"),
        "other-eligibility-requirements.pdf": ("other-eligibility-requirements", "Other Eligibility Requirements"),
        "reference.pdf": ("reference", "Reference"),
        "masterindex.pdf": ("master-index", "Cumulative/Master Index"),
    }
    families = {"manual_chapter_pdf": {"found": 0, "taken": 0}, "full_manual_pdf": {"found": 0, "taken": 0},
                "update_archive_pdf_or_html": {"found": 0, "taken": 0}}
    docs = []
    for href, text in links(page, index):
        if "/reference/mrg/" not in href:
            continue
        name = href.rsplit("/", 1)[-1]
        if name in chapters:
            label, heading = chapters[name]
            families["manual_chapter_pdf"]["found"] += 1
            families["manual_chapter_pdf"]["taken"] += 1
            docs.append(document("us-ny", label=label, title=f"New York Medicaid Reference Guide: {heading}", url=href, fmt="pdf",
                                 authority="New York State Department of Health", manual="New York Medicaid Reference Guide (MRG)",
                                 index_url=index, subtype="eligibility_manual_chapter_pdf",
                                 request={"browser_impersonation": True}, extraction={"ocr": True},
                                 extra={"agency": "doh", "extraction_granularity": "pdf_page",
                                        "request_note": "health.ny.gov returns 403 to the Axiom user agent; browser_impersonation is the existing manifest option for that"}))
        elif name == "mrg.pdf":
            families["full_manual_pdf"]["found"] += 1
        elif re.search(r"\d{4}", name):
            families["update_archive_pdf_or_html"]["found"] += 1
    return docs, {"index_url": index, "families": families}


def build_nc() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = "https://policies.ncdhhs.gov/divisional-a-m/health-benefits-nc-medicaid/"
    pages = {
        "abd": (root + "adult-medicaid/abd-policies-manuals/", "Aged, Blind and Disabled Medicaid Manual"),
        "fcm": (root + "family-and-childrens-medicaid/fcm-policies-manuals/", "Family and Children's Medicaid Manual"),
        "basic": (root + "basic-medicaid-eligibility-requirements/", "Basic Medicaid Eligibility Requirements"),
    }
    other = {
        "abd_administrative_letters": root + "adult-medicaid/abd-administrative-letters/",
        "abd_change_notices": root + "adult-medicaid/abd-change-notices/",
        "fcm_administrative_letters": root + "family-and-childrens-medicaid/fcm-administrative-letters/",
        "fcm_change_notices": root + "family-and-childrens-medicaid/fcm-change-notices/",
        "dhb_forms": root + "dhb-forms/",
        "eligibility_information_system": root + "eligibility-information-system-eis/",
    }
    row_re = re.compile(r'<tr id="post-row-\d+".*?</tr>', re.S)
    title_re = re.compile(r'<td><a href="[^"]+"\s*>(.*?)</a></td>', re.S)
    open_re = re.compile(r'<a href="([^"]+\.pdf)" class="dlp-download-link', re.I)
    docs: list[dict[str, Any]] = []
    families: dict[str, dict[str, int]] = {}
    seen_labels: set[str] = set()
    for key, (url, manual) in pages.items():
        page = fetch(url)
        fam = families.setdefault(f"{key}_manual_section_pdf", {"found": 0, "taken": 0})
        for row in row_re.findall(page):
            t, o = title_re.search(row), open_re.search(row)
            if not (t and o):
                continue
            title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t.group(1)))).strip()
            href = html.unescape(o.group(1))
            fam["found"] += 1
            m = re.match(r"^MA[-\s]*(\d{3,4})(?:-([A-Z])(?![A-Za-z]))?(?![0-9])", title)
            if m:
                label = f"ma-{m.group(1)}" + (f"-{m.group(2).lower()}" if m.group(2) else "")
            elif key == "basic":
                label = "basic-medicaid-eligibility-requirements"
            else:
                label = f"{key}-{slug(title, 50)}"
            if label in seen_labels:
                label = f"{label}-{fam['found']}"
            seen_labels.add(label)
            fam["taken"] += 1
            docs.append(document("us-nc", label=label, title=f"North Carolina {manual}: {title}", url=href, fmt="pdf",
                                 authority="North Carolina Department of Health and Human Services, Division of Health Benefits (NC Medicaid)",
                                 manual=manual, index_url=url, subtype="eligibility_manual_section_pdf",
                                 extraction={"ocr": True}, extra={"agency": "dhb", "extraction_granularity": "pdf_page", "manual_part": key}))
    for name, url in other.items():
        page = fetch(url)
        families[name] = {"found": len(set(re.findall(r'href="([^"]+\.pdf)"', page, re.I))), "taken": 0}
    return docs, {"index_url": root, "families": families}


def build_ga() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://pamms.dhs.ga.gov/dfcs/medicaid/"
    page = fetch(index)
    families = {"manual_section_html": {"found": 0, "taken": 0}, "appendix_html": {"found": 0, "taken": 0},
                "toc_page_html": {"found": 0, "taken": 0}, "pdf_export": {"found": 0, "taken": 0},
                "mt_cover_letter_pdf": {"found": 0, "taken": 0}}
    docs = []

    def add(label: str, title: str, url: str) -> None:
        docs.append(document("us-ga", label=label, title=f"Georgia Medicaid Policy Manual: {title}", url=url, fmt="html",
                             authority="Georgia Department of Human Services, Division of Family and Children Services",
                             manual="Georgia DFCS Medicaid Policy Manual (ODIS/PAMMS)", index_url=index,
                             subtype="eligibility_manual_section", extraction={"html_content_selector": "article.doc"},
                             extra={"agency": "dfcs"}))

    for href, text in links(page, index):
        rel = href[len(index):] if href.startswith(index) else None
        if rel is None:
            if href.endswith("_exports/medicaid.pdf"):
                families["pdf_export"]["found"] += 1
            continue
        if re.fullmatch(r"\d{4}/", rel):
            families["manual_section_html"]["found"] += 1
            families["manual_section_html"]["taken"] += 1
            add(rel.strip("/"), text, href)
        elif rel.endswith("-toc/") or rel == "manual-toc/":
            families["toc_page_html"]["found"] += 1
            if rel == "appendix-h-medicaid-admin-review-toc/":
                sub = fetch(href)
                for shref, stext in links(sub, href):
                    if "/dfcs/medicaid/appendix-h/" in shref:
                        families["appendix_html"]["found"] += 1
                        families["appendix_html"]["taken"] += 1
                        add("appendix-h-" + shref.rstrip("/").rsplit("/", 1)[-1], f"Appendix H {stext}", shref)
            elif rel == "appendix-g-cover-letters-toc/":
                sub = fetch(href)
                families["mt_cover_letter_pdf"]["found"] = len({h for h, _ in links(sub, href) if "cover-letter" in h})
        elif rel.startswith("appendix-"):
            families["appendix_html"]["found"] += 1
            families["appendix_html"]["taken"] += 1
            add(rel.strip("/"), text, href)
    return docs, {"index_url": index, "families": families}


def build_tx() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Crawl the two HHSC handbooks from their index pages.

    Pages carry either policy text (``article.c-article div.c-field--name-body``) or only a
    "Pages in this section" sub-menu (``.c-view--hb-submenus``); many carry both. Text-bearing
    pages become documents; menu-only pages are counted as landing pages.
    """
    from bs4 import BeautifulSoup

    host = "https://fhb.hhs.texas.gov"
    mepd = host + "/handbooks/medicaid-elderly-people-disabilities-handbook"
    twh = host + "/handbooks/texas-works-handbook"
    families: dict[str, dict[str, int]] = {}
    docs = []
    seen: set[str] = set()

    def crawl(start: str, *, handbook: str, prefix: str, manual: str, family: str, label_re: str) -> None:
        fam = families.setdefault(f"{family}_html", {"found": 0, "taken": 0})
        landing = families.setdefault(f"{family}_landing_html", {"found": 0, "taken": 0})
        queue = [start]
        while queue:
            url = queue.pop(0)
            if url in seen or not url.startswith(handbook + "/"):
                continue
            seen.add(url)
            soup = BeautifulSoup(fetch(url), "html.parser")
            heading = soup.select_one("h1.c-page-title")
            title = re.sub(r"\s+", " ", heading.get_text(" ", strip=True)) if heading else url.rsplit("/", 1)[-1]
            children = [urljoin(url, str(a["href"])).split("#", 1)[0] for a in soup.select(".c-view--hb-submenus a[href]")]
            queue.extend(children)
            m = re.match(re.escape(handbook) + "/" + label_re, url)
            if url == start or m is None:
                landing["found"] += 1
                continue
            if soup.select_one("article.c-article div.c-field--name-body") is None:
                landing["found"] += 1
                continue
            fam["found"] += 1
            fam["taken"] += 1
            docs.append(document("us-tx", label=f"{prefix}-{m.group(1)}", title=f"{manual}: {title}", url=url, fmt="html",
                                 authority="Texas Health and Human Services Commission", manual=manual,
                                 index_url=mepd if prefix == "mepd" else twh, subtype="eligibility_handbook_section",
                                 extraction={"html_content_selector": "article.c-article div.c-field--name-body",
                                             "html_drop_selectors": [".c-field__label"]},
                                 extra={"agency": "hhsc"}))

    mepd_manual = "Medicaid for the Elderly and People with Disabilities Handbook"
    index_page = fetch(mepd)
    chapters = [h for h, _ in links(index_page, mepd) if h.startswith(mepd + "/chapter-")]
    families["mepd_chapter_landing_html"] = {"found": len(chapters), "taken": 0}
    for chref in chapters:
        seen.discard(chref)
        crawl(chref, handbook=mepd, prefix="mepd", manual=mepd_manual, family="mepd_section", label_re=r"([a-r]-\d{4})-")
    crawl(mepd + "/mepd-appendices", handbook=mepd, prefix="mepd", manual=mepd_manual, family="mepd_appendix", label_re=r"(appendix-[a-z]+)-")
    glossary = mepd + "/mepd-glossary"
    families["mepd_glossary_html"] = {"found": 1, "taken": 1}
    docs.append(document("us-tx", label="mepd-glossary", title=f"{mepd_manual}: MEPD Glossary", url=glossary, fmt="html",
                         authority="Texas Health and Human Services Commission", manual=mepd_manual, index_url=mepd,
                         subtype="eligibility_handbook_section",
                         extraction={"html_content_selector": "article.c-article div.c-field--name-body",
                                     "html_drop_selectors": [".c-field__label"]}, extra={"agency": "hhsc"}))
    other = [t for h, t in links(index_page, mepd) if h.startswith(mepd + "/mepd-") and "glossary" not in h and "appendices" not in h]
    families["mepd_forms_notices_revisions_bulletins_pages"] = {"found": len(other), "taken": 0}

    twh_page = fetch(twh)
    parts = [(h, t) for h, t in links(twh_page, twh) if h.startswith(twh + "/part-")]
    families["twh_part_landing_html"] = {"found": len(parts), "taken": 0}
    part_a = twh + "/part-a-determining-eligibility"
    crawl(part_a, handbook=twh, prefix="twh", manual="Texas Works Handbook", family="twh_part_a_section", label_re=r"(a-\d{3,4})-")
    for phref, ptext in parts:
        if phref == part_a:
            continue
        n = len({h for h, _ in links(fetch(phref), phref) if re.match(re.escape(twh) + r"/[a-z]-\d{3,4}-", h)})
        families[f"twh_{slug(ptext.split(',')[0])}_chapters_html"] = {"found": n, "taken": 0}
    return docs, {"index_url": mepd, "twh_index_url": twh, "families": families}


def build_pa() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # RoboHelp output; the topic list lives in whxdata/toc.new.js and nested tocN.new.js
    base = "http://services.dpw.state.pa.us/oimpolicymanuals/ma/"
    index = base + "index.htm"
    fetch(index)

    def toc(key: str) -> list[dict[str, Any]]:
        text = fetch(f"{base}whxdata/{key}.new.js")
        m = re.search(r"var toc =\s*(\[.*?\]);\s*window", text, re.S)
        return json.loads(m.group(1)) if m else []

    entries: list[tuple[str, str, str]] = []  # (chapter name, topic name, url)

    def walk(key: str, chapter: str | None) -> None:
        for item in toc(key):
            name, url = item.get("name", ""), item.get("url")
            top = chapter or name
            if url:
                # anchors point into the same topic page; the page is the document
                entries.append((top, name, base + url.split("#", 1)[0]))
            if item.get("type") == "book" and item.get("key"):
                walk(item["key"], top)

    walk("toc", None)
    families = {"handbook_topic_html": {"found": 0, "taken": 0}, "forms_opsmemo_policy_clarification_catalog_html": {"found": 0, "taken": 0}}
    docs = []
    seen: set[str] = set()
    for chapter, name, url in entries:
        if url in seen:
            continue
        seen.add(url)
        if chapter.startswith("300 "):
            families["forms_opsmemo_policy_clarification_catalog_html"]["found"] += 1
            continue
        families["handbook_topic_html"]["found"] += 1
        families["handbook_topic_html"]["taken"] += 1
        rel = re.sub(r"\.htm$", "", url[len(base):])
        label = "/".join(slug(part, 100) for part in rel.split("/"))
        docs.append(document("us-pa", label=label, title=f"Pennsylvania Medical Assistance Eligibility Handbook: {name}", url=url, fmt="html",
                             authority="Pennsylvania Department of Human Services, Office of Income Maintenance",
                             manual="Pennsylvania Medical Assistance Eligibility Handbook", index_url=index,
                             subtype="eligibility_handbook_topic",
                             extraction={"html_drop_selectors": [".topic-header", ".topic-header-shadow"]},
                             extra={"agency": "dhs", "handbook_chapter": chapter,
                                    "transport_note": "publisher serves the handbook over plain http only; https connections time out"}))
    return docs, {"index_url": index, "families": families}


def build_ar() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://humanservices.arkansas.gov/divisions-shared-services/county-operations/division-policies/"
    page = fetch(index)
    wanted = {"Medical Services Policy Manual": ("policy-manual", "Arkansas Medical Services Policy Manual"),
              "Medical Services Appendices": ("appendices", "Arkansas Medical Services Policy Manual: Appendices")}
    families = {"medical_services_manual_pdf": {"found": 0, "taken": 0}, "other_program_manual_pdf": {"found": 0, "taken": 0}}
    docs = []
    for href, text in links(page, index):
        if not href.lower().endswith(".pdf"):
            continue
        if text in wanted:
            label, title = wanted[text]
            families["medical_services_manual_pdf"]["found"] += 1
            families["medical_services_manual_pdf"]["taken"] += 1
            docs.append(document("us-ar", label=label, title=title, url=href, fmt="pdf",
                                 authority="Arkansas Department of Human Services, Division of County Operations",
                                 manual="Arkansas Medical Services Policy Manual", index_url=index,
                                 subtype="eligibility_manual_pdf", extraction={"ocr": True},
                                 extra={"agency": "dco", "extraction_granularity": "pdf_page"}))
        else:
            families["other_program_manual_pdf"]["found"] += 1
    return docs, {"index_url": index, "families": families}


def build_nj() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = "https://www.nj.gov/humanservices/notices/rules-and-fees/rules-and-regulations/"
    page = fetch(index)
    wanted = {"10:69": "AFDC-Related Medicaid", "10:70": "Medically Needy Program", "10:71": "Medicaid Only",
              "10:72": "New Jersey Care Special Medicaid Programs Manual", "10:78": "NJ FamilyCare",
              "10:79": "NJ FamilyCare - Children's Program"}
    families = {"medicaid_eligibility_chapter_pdf": {"found": 0, "taken": 0}, "other_title_10_chapter_pdf": {"found": 0, "taken": 0}}
    docs = []
    for href, text in links(page, index):
        if not re.match(r"^10:\d+[A-Z]?$", text):
            continue
        if text in wanted:
            families["medicaid_eligibility_chapter_pdf"]["found"] += 1
            families["medicaid_eligibility_chapter_pdf"]["taken"] += 1
            docs.append(document("us-nj", label=f"njac-{slug(text)}", title=f"New Jersey Medicaid Eligibility Manuals: N.J.A.C. {text} {wanted[text]}",
                                 url=href, fmt="pdf",
                                 authority="New Jersey Department of Human Services (Office of Legal and Regulatory Affairs; Division of Medical Assistance and Health Services)",
                                 manual="New Jersey Medicaid Eligibility and Service Manuals (N.J.A.C. Title 10)", index_url=index,
                                 subtype="eligibility_manual_chapter_pdf", extraction={"ocr": True},
                                 extra={"agency": "dhs", "extraction_granularity": "pdf_page", "njac_chapter": text}))
        else:
            families["other_title_10_chapter_pdf"]["found"] += 1
    return docs, {"index_url": index, "families": families}


BUILDERS = {"us-va": build_va, "us-ny": build_ny, "us-nc": build_nc, "us-ga": build_ga,
            "us-tx": build_tx, "us-pa": build_pa, "us-ar": build_ar, "us-nj": build_nj}
NAMES = {"us-ar": "Arkansas", "us-va": "Virginia", "us-ca": "California", "us-tx": "Texas", "us-fl": "Florida",
         "us-ny": "New York", "us-pa": "Pennsylvania", "us-il": "Illinois", "us-oh": "Ohio", "us-ga": "Georgia",
         "us-nc": "North Carolina", "us-mi": "Michigan", "us-nj": "New Jersey"}
SOURCE_KIND = {"us-va": "official_pdf_manual_chapters", "us-ny": "official_pdf_manual_chapters", "us-nc": "official_pdf_manual_sections",
               "us-ga": "official_html_manual_sections", "us-tx": "official_html_handbook_sections",
               "us-pa": "official_html_handbook_topics", "us-ar": "official_pdf_manual", "us-nj": "official_pdf_njac_chapters"}

STATIC_ROWS: dict[str, dict[str, Any]] = {
    "us": {
        "queue_status": "needs_review",
        "source_kind": "federal_regulation_ecfr",
        "primary_source_url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-435",
        "target_manifest": None,
        "target_scope": {"jurisdiction": "us", "document_class": "regulation", "version": "2026-06-25-title-42-part-435"},
        "index_url": "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Batch 1 finding (2026-09-10): 42 CFR part 435 is already in the corpus as us/regulation version "
                  "2026-06-25-title-42-part-435 (coverage complete, 168 provisions) plus the CMS-2454-IFC community-engagement "
                  "scopes; 42 CFR part 436 (Puerto Rico, Guam, Virgin Islands eligibility) is NOT in the corpus (no coverage, "
                  "manifest, or ingest-run note mentions part 436). Nothing federal was re-ingested and none of the federal lead-list "
                  "URLs were taken in this run. A later run should extract part 436 through extract-ecfr --only-title 42 --only-part 436."),
    },
    "us-ca": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_pdf_manual_articles",
        "primary_source_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "target_manifest": "manifests/us-ca-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-ca", "document_class": "manual", "version": VERSION},
        "index_url": "https://www.dhcs.ca.gov/services/medi-cal/eligibility/Pages/MEPM.aspx",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: the DHCS Medi-Cal Eligibility Procedures Manual (MEPM) index returns HTTP 403 with an Imperva/Incapsula "
                  "'Request unsuccessful' interstitial (incident id 648000110623365723-464410415712436979) for the Axiom user agent, a plain "
                  "browser user agent, and curl-cffi impersonation profiles chrome120, chrome131, safari17_0, firefox133 and edge101 "
                  "(the existing manifest browser_impersonation option). No workaround attempted. Index inventory not possible."),
    },
    "us-oh": {
        "queue_status": "blocked_primary_source",
        "source_kind": "official_html_oac_rules_and_mepl",
        "primary_source_url": "https://codes.ohio.gov/ohio-administrative-code/5160:1",
        "target_manifest": "manifests/us-oh-medicaid-eligibility-manual.yaml",
        "target_scope": {"jurisdiction": "us-oh", "document_class": "manual", "version": VERSION},
        "index_url": "https://medicaid.ohio.gov/resources-for-providers/policies-guidelines/medicaid-eligibility-procedure-letters/",
        "index_document_count": None, "taken_count": 0,
        "notes": ("Blocked 2026-09-10: Ohio's eligibility manual is OAC 5160:1 (Ohio Laws and Administrative Rules, codes.ohio.gov, the same "
                  "publisher used for the OH SNAP rules scope) with ODM Medicaid Eligibility Procedure Letters on medicaid.ohio.gov. "
                  "codes.ohio.gov: TCP connect to 198.234.74.32:443 times out (curl 28 after 60-75 s, curl-cffi chrome120 the same, "
                  "WebFetch ECONNREFUSED). medicaid.ohio.gov and ohio.gov: every path including the site root returns HTTP 404 "
                  "(5,279-byte error page) from this client and from WebFetch. Only the dam.assets.ohio.gov asset host answers. "
                  "No workaround attempted; retry from another network before assuming a permanent block."),
    },
    "us-fl": {
        "queue_status": "done",
        "source_kind": "official_html_combined_manual",
        "primary_source_url": "https://www.myflfamilies.com/services/public-assistance/ess-program-policy-manual",
        "target_manifest": "manifests/us-fl-ess-manual.yaml",
        "target_scope": {"jurisdiction": "us-fl", "document_class": "manual", "version": "2026-05-27-fl-ess-manual-r2026-07-15-self-contained"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Florida DCF ESS Program Policy Manual (manifests/us-fl-ess-manual.yaml, 48 documents) carries the "
                  "Medicaid eligibility chapters (1400/1600/1800 MFAM-MSSI, 2000 Coverage Groups, 2200 Standard Filing Unit, 2400 Budgeting, "
                  "2600 Calculation of Benefits, Appendix A-7 Family-Related Medicaid income limits, A-9 SSI-related standards, A-9.1 MSP). "
                  "Not duplicated in batch 1; does not count toward the batch, Michigan pulled instead (itself already covered), then New Jersey."),
    },
    "us-il": {
        "queue_status": "done",
        "source_kind": "official_html_combined_manual",
        "primary_source_url": "https://www.dhs.state.il.us/page.aspx?item=13473",
        "target_manifest": "manifests/us-il-snap-manual.yaml",
        "target_scope": {"jurisdiction": "us-il", "document_class": "manual", "version": "2026-05-27-il-cash-snap-medical-manual-r2026-07-15-self-contained"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Illinois DHS Cash, SNAP and Medical Manual (manifests/us-il-snap-manual.yaml, 4,750 documents) includes "
                  "PM/WAG 15 Eligibility for Medical Only Programs, PM/WAG 20 Medical Program and the medical-program sub-sections. "
                  "Not duplicated in batch 1; does not count toward the batch, North Carolina pulled instead."),
    },
    "us-mi": {
        "queue_status": "done",
        "source_kind": "official_pdf_combined_manual",
        "primary_source_url": "https://mdhhs-pres-prod.michigan.gov/OLMWeb/ex/BP/Public/BEM/000.pdf",
        "target_manifest": "manifests/us-mi-bridges-manual.yaml",
        "target_scope": {"jurisdiction": "us-mi", "document_class": "manual", "version": "2026-07-17-mi-bridges-manual"},
        "index_url": None, "index_document_count": None, "taken_count": 0,
        "notes": ("Already in corpus: Michigan Bridges Eligibility Manual (manifests/us-mi-bridges-manual.yaml, 196 documents) carries the MA "
                  "chapters BEM 105-174, 211, 260, 402, 405, 530-547. Pulled as the replacement for Florida, found covered, so New Jersey was "
                  "pulled next. Does not count toward the batch."),
    },
}


def main() -> int:
    queue = yaml.safe_load(QUEUE.read_text())
    rows = {s["jurisdiction"]: s for s in queue["states"]}
    summary: dict[str, Any] = {}
    for jur, build in BUILDERS.items():
        docs, info = build()
        if not docs:
            print(f"{jur}: no documents found; index layout changed?", file=sys.stderr)
            return 1
        paths = [d["citation_path"] for d in docs]
        if len(set(paths)) != len(paths):
            dupes = sorted({p for p in paths if paths.count(p) > 1})
            print(f"{jur}: duplicate citation paths {dupes}", file=sys.stderr)
            return 1
        stem = f"{jur}-medicaid-eligibility-manual"
        (ROOT / "manifests" / f"{stem}.yaml").write_text(
            yaml.safe_dump({"version": VERSION, "documents": docs}, sort_keys=False, allow_unicode=True, width=120))
        found = sum(f["found"] for f in info["families"].values())
        taken = sum(f["taken"] for f in info["families"].values())
        summary[jur] = {"documents": len(docs), **info}
        row = rows.get(jur) or {"jurisdiction": jur, "name": NAMES[jur], "lead_counts": {}, "candidate_sources": []}
        row.update({
            "name": NAMES[jur], "queue_status": "agent_ready", "source_kind": SOURCE_KIND[jur],
            "primary_source_url": docs[0]["source_url"], "target_manifest": f"manifests/{stem}.yaml",
            "target_scope": {"jurisdiction": jur, "document_class": "manual", "version": VERSION},
            "index_url": info["index_url"], "index_document_count": found, "taken_count": taken,
            "index_families": info["families"],
            "notes": (f"Batch 1 (2026-09-10): {len(docs)} manual documents taken from the publisher's own index ({found} documents inventoried "
                      f"across {len(info['families'])} families; {taken} taken). Extraction proven with the official-documents extractor; "
                      "see docs/ingest-runs/2026-09-10-medicaid-state-eligibility-manuals-batch-1.md."),
        })
        rows[jur] = row
        print(f"{jur}: {len(docs)} documents; index families {info['families']}")
    for jur, static in STATIC_ROWS.items():
        row = rows.get(jur) or {"jurisdiction": jur, "name": NAMES.get(jur, "Federal"), "lead_counts": {}, "candidate_sources": []}
        row.update(static)
        rows[jur] = row
    queue["states"] = [rows[j] for j in sorted(rows, key=lambda j: (j != "us", j))]
    queue["status_counts"] = {}
    for s in queue["states"]:
        queue["status_counts"][s["queue_status"]] = queue["status_counts"].get(s["queue_status"], 0) + 1
    queue["queue_status"] = "in_progress"
    batch_note = ("Batch 1 (2026-09-10): the two queued state rows plus the eight largest states by population; done-already states "
                  "are replaced by the next largest. Generator: scripts/build_medicaid_state_eligibility_manual_manifests.py.")
    notes = queue.setdefault("policy", {}).setdefault("notes", [])
    if batch_note not in notes:
        notes.append(batch_note)
    QUEUE.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True, width=120))
    print(json.dumps(summary, indent=1))
    print(f"queue {queue['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
