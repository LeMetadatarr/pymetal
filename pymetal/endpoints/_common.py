"""Helpers shared by endpoint modules."""
from __future__ import annotations

import re
from typing import List, Optional

from lxml import html as lxml_html

from pymetal.locators import RE_TRAILING_ID
from pymetal.models import Audit


def parse_html(content: bytes):
    return lxml_html.fromstring(content)


def dl_pairs(dl_element) -> dict:
    """Extract {label: value} from a <dl><dt>...</dt><dd>...</dd>...</dl>.

    metal-archives stat blocks pair each <dt> label (e.g. "Country of origin:")
    with the following <dd> value. Order varies, so positional XPaths break;
    label-keyed extraction is robust to MA reshuffling fields.
    """
    out = {}
    last_dt: Optional[str] = None
    for child in dl_element:
        text = (child.text_content() or "").strip()
        if child.tag == "dt":
            last_dt = text.rstrip(":").strip()
        elif child.tag == "dd" and last_dt is not None:
            out[last_dt] = text
            # capture link href if present (e.g. label, country)
            links = child.xpath("./a/@href")
            if links:
                out[last_dt + " :href"] = links[0]
            last_dt = None
    return out


def collect_stats(tree, dl_xpath: str) -> dict:
    """Merge dt/dd pairs from every matching <dl>."""
    merged: dict = {}
    for dl in tree.xpath(dl_xpath):
        merged.update(dl_pairs(dl))
    return merged


_AUDIT_LABEL_RE = re.compile(
    r"(Added by|Modified by|Added on|Last modified on)\s*:\s*(.+)",
    re.IGNORECASE,
)


def extract_audit(tree) -> Optional[Audit]:
    """Parse the auditTrail block present on every band/release/artist page."""
    cells = tree.xpath('//*[@id="auditTrail"]//td')
    if not cells:
        return None
    fields: dict = {}
    for td in cells:
        text = re.sub(r"\s+", " ", td.text_content() or "").strip()
        m = _AUDIT_LABEL_RE.match(text)
        if not m:
            continue
        label, value = m.group(1).lower(), m.group(2).strip()
        if label == "added by":
            fields["added_by"] = value
        elif label == "modified by":
            fields["modified_by"] = value
        elif label == "added on":
            fields["added_on"] = value
        elif label == "last modified on":
            fields["last_modified_on"] = value
    return Audit(**fields) if fields else None


def parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    m = re.search(r"-?\d+", value)
    return int(m.group(0)) if m else None


def first(xs: List[str]) -> Optional[str]:
    for x in xs:
        s = x.strip() if isinstance(x, str) else x
        if s and s != "N/A":
            return s
    return None


def split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    # MA uses "," and sometimes ";" or " | "
    parts = re.split(r"[,;|]", value)
    return [p.strip() for p in parts if p.strip()]


def ma_id_from_url(url: Optional[str]) -> Optional[int]:
    if not url:
        return None
    m = RE_TRAILING_ID.search(url.rstrip("/"))
    return int(m.group("id")) if m else None
