"""Label detail endpoint."""
from __future__ import annotations

import re
from typing import Optional

from pymetal.endpoints._common import (
    collect_stats,
    extract_audit,
    first,
    ma_id_from_url,
    parse_html,
)
from pymetal.http import Client, default_client
from pymetal.locators import URL_LABEL
from pymetal.models import Label


def get_label(label_id: int, client: Optional[Client] = None) -> Label:
    """Fetch a label's detail page."""
    c = client or default_client
    resp = c.get(URL_LABEL.format(label_id=label_id))
    tree = parse_html(resp.content)

    name = first(tree.xpath("//h1//text()")) or ""
    stats = collect_stats(tree, '//*[@id="label_info"]//dl')

    sub_labels_raw = stats.get("Sub-labels")
    sub_labels = []
    if sub_labels_raw:
        sub_labels = [s.strip() for s in re.split(r"[,;\n]", sub_labels_raw) if s.strip()]

    parent_href = stats.get("Parent label :href")
    logo = first(
        tree.xpath('//*[@id="label_logo"]//img/@src')
        + tree.xpath('//*[@id="logo"]//img/@src')
    )
    website = stats.get("Website :href") or stats.get("Website")
    if website and not website.startswith("http"):
        website = None

    return Label(
        ma_id=label_id,
        name=name.strip(),
        country=stats.get("Country"),
        status=stats.get("Status"),
        address=stats.get("Address"),
        phone=stats.get("Phone number"),
        email=stats.get("E-mail"),
        website=website,
        styles=stats.get("Styles/specialties") or stats.get("Specialised in"),
        founding_date=stats.get("Founding date"),
        sub_labels=sub_labels,
        parent_label_id=ma_id_from_url(parent_href),
        parent_label_name=stats.get("Parent label"),
        online_shopping=stats.get("Online shopping"),
        logo_url=logo,
        audit=extract_audit(tree),
    )
