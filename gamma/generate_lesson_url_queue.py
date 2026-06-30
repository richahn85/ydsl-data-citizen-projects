#!/usr/bin/env python3
"""Build the Gamma lesson-page URL queue from the published site files."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import quote


SITE_BASE_URL = "https://richahn85.github.io/ydsl-data-citizen-projects"
ROOT = Path(__file__).resolve().parents[1]
TEACHING_DIR = ROOT / "pages" / "teaching"
CSV_PATH = ROOT / "gamma" / "lesson_page_urls.csv"
TXT_PATH = ROOT / "gamma" / "lesson_page_urls.txt"


def extract_title(html_path: Path) -> str:
    html = html_path.read_text(encoding="utf-8")
    match = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return html_path.parent.name
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title.split(" · ", 1)[0]


def project_number(slug: str) -> int:
    match = re.match(r"^(\d+)-", slug)
    if not match:
        return 999
    return int(match.group(1))


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for project_dir in sorted(TEACHING_DIR.iterdir(), key=lambda path: project_number(path.name)):
        if not project_dir.is_dir():
            continue
        html_path = project_dir / "lesson-plan.html"
        if not html_path.exists():
            continue
        slug = project_dir.name
        no = f"{project_number(slug):02d}"
        encoded_slug = quote(slug)
        rows.append(
            {
                "project_no": no,
                "title": extract_title(html_path),
                "slug": slug,
                "lesson_url": f"{SITE_BASE_URL}/pages/teaching/{encoded_slug}/lesson-plan.html",
                "local_html_path": str(html_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return rows


def main() -> None:
    rows = build_rows()
    if len(rows) != 30:
        raise SystemExit(f"Expected 30 lesson pages, found {len(rows)}.")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["project_no", "title", "slug", "lesson_url", "local_html_path"],
        )
        writer.writeheader()
        writer.writerows(rows)

    TXT_PATH.write_text(
        "\n".join(row["lesson_url"] for row in rows) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(rows)} URLs")
    print(CSV_PATH)
    print(TXT_PATH)


if __name__ == "__main__":
    main()
