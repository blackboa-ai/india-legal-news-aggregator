#!/usr/bin/env python3
"""
Dynamic XML Sitemap Generator for India Legal News Aggregator.
Fetches active court judgments, legal categories, and court codes,
and builds an SEO-optimized sitemap.xml for Google Search Console.
"""

import datetime
import html
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://india-legal-news.vercel.app"
API_URL = "https://india-legal-news-api.onrender.com/api/v1"

COURT_CODES = [
    "sc",
    "delhi-hc",
    "bombay-hc",
    "madras-hc",
    "calcutta-hc",
    "allahabad-hc",
    "karnataka-hc",
    "kerala-hc",
    "gujarat-hc",
    "punjab-haryana-hc",
    "patna-hc",
    "rajasthan-hc",
]

CATEGORIES = [
    "Criminal",
    "Constitutional",
    "Corporate",
    "Civil",
    "Taxation",
    "Human Rights",
    "Labor",
    "Environmental",
    "Family",
    "Cyber & IT",
]

CONTENT_TYPES = ["judgment", "news"]


def fetch_live_judgments(max_items: int = 500) -> list[dict]:
    all_items: list[dict] = []
    offset = 0
    page_size = 100

    while len(all_items) < max_items:
        url = f"{API_URL}/judgments?limit={page_size}&offset={offset}"
        req = urllib.request.Request(url, headers={"User-Agent": "SitemapGenerator/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data") or data.get("items") or []
                if not items:
                    break
                all_items.extend(items)
                total = data.get("total", len(all_items))
                offset += len(items)
                if offset >= total:
                    break
        except Exception as e:
            print(f"Warning: Could not fetch from production API ({e}). Falling back to seed dataset.")
            break

    return all_items


def generate_sitemap(output_path: Path):
    today = datetime.date.today().isoformat()
    judgments = fetch_live_judgments(max_items=500)

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
        "",
        "  <!-- Primary Homepage -->",
        "  <url>",
        f"    <loc>{BASE_URL}/</loc>",
        f"    <lastmod>{today}</lastmod>",
        "    <changefreq>hourly</changefreq>",
        "    <priority>1.0</priority>",
        "  </url>",
        "",
        "  <!-- Court Precedent Hubs -->",
    ]

    for code in COURT_CODES:
        court_url = f"{BASE_URL}/?court={code}"
        xml_lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(court_url)}</loc>",
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>daily</changefreq>",
                "    <priority>0.85</priority>",
                "  </url>",
            ]
        )

    xml_lines.append("\n  <!-- Subject Category Law Hubs -->")
    for cat in CATEGORIES:
        escaped_cat = urllib.parse.quote(cat)
        cat_url = f"{BASE_URL}/?category={escaped_cat}"
        xml_lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(cat_url)}</loc>",
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>daily</changefreq>",
                "    <priority>0.80</priority>",
                "  </url>",
            ]
        )

    xml_lines.append("\n  <!-- Content Type Hubs -->")
    for ctype in CONTENT_TYPES:
        type_url = f"{BASE_URL}/?type={ctype}"
        xml_lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(type_url)}</loc>",
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>daily</changefreq>",
                "    <priority>0.75</priority>",
                "  </url>",
            ]
        )

    if judgments:
        xml_lines.append(f"\n  <!-- Live Judgments & Precedent Pages ({len(judgments)} items) -->")
        for item in judgments:
            item_id = item.get("id")
            if not item_id:
                continue
            item_url = f"{BASE_URL}/?judgment={item_id}"
            date_val = item.get("judgment_date") or today
            xml_lines.extend(
                [
                    "  <url>",
                    f"    <loc>{html.escape(item_url)}</loc>",
                    f"    <lastmod>{date_val}</lastmod>",
                    "    <changefreq>weekly</changefreq>",
                    "    <priority>0.70</priority>",
                    "  </url>",
                ]
            )

    xml_lines.append("</urlset>\n")

    content = "\n".join(xml_lines)
    output_path.write_text(content, encoding="utf-8")
    print(f"Successfully generated {output_path} with {len(xml_lines)} lines")


if __name__ == "__main__":
    out = Path("frontend/public/sitemap.xml")
    generate_sitemap(out)
