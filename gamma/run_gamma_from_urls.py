#!/usr/bin/env python3
"""Create Gamma presentations sequentially from the 30 published lesson URLs.

The script intentionally uses only the Python standard library so it can run on
the school computer without installing extra packages.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


API_BASE = "https://public-api.gamma.app/v1.0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "gamma" / "lesson_page_urls.csv"
DEFAULT_OUT = ROOT / "gamma" / "gamma_results.csv"
DEFAULT_DOWNLOAD_DIR = ROOT / "gamma" / "pptx"


class ArticleTextParser(HTMLParser):
    """Extract readable text and image URLs from the article content."""

    BLOCK_TAGS = {
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "ol",
        "p",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_article = False
        self.article_depth = 0
        self.skip_depth = 0
        self.parts: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key: value or "" for key, value in attrs}
        if tag == "article" and "content" in attrs_map.get("class", "").split():
            self.in_article = True
            self.article_depth = 1
            self.parts.append("\n")
            return

        if not self.in_article:
            return

        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return

        self.article_depth += 1

        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")
        if tag == "img":
            src = attrs_map.get("src", "").strip()
            if src:
                absolute = urllib.parse.urljoin(self.base_url, src)
                alt = attrs_map.get("alt", "").strip()
                label = f"Image: {alt}" if alt else "Image"
                self.images.append(f"{label}\n{absolute}")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth:
            if tag in {"script", "style", "noscript"}:
                self.skip_depth -= 1
            return

        if self.in_article:
            if tag in self.BLOCK_TAGS:
                self.parts.append("\n")
            self.article_depth -= 1
            if tag == "article" or self.article_depth <= 0:
                self.in_article = False
                self.article_depth = 0

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self.in_article:
            self.parts.append(text + " ")

    def text(self) -> str:
        body = html.unescape("".join(self.parts))
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = "\n".join(line.strip() for line in body.splitlines())
        body = body.strip()
        if self.images:
            body += "\n\nProvided image URLs for visual slides:\n" + "\n\n".join(self.images[:8])
        return body


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_existing_results(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row.get("project_no", ""): row for row in csv.DictReader(handle)}


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "project_no",
        "title",
        "lesson_url",
        "generation_id",
        "status",
        "gamma_url",
        "export_url",
        "pptx_path",
        "credits_deducted",
        "credits_remaining",
        "error",
        "updated_at",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def http_json(
    method: str,
    url: str,
    *,
    api_key: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {error_body}") from exc


def fetch_text(url: str, timeout: int = 60) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YDSL-Gamma-Queue/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def extract_article_text(url: str) -> str:
    parser = ArticleTextParser(url)
    parser.feed(fetch_text(url))
    text = parser.text()
    if len(text) < 500:
        raise RuntimeError(f"Extracted text is unexpectedly short from {url}")
    return text


def make_input_text(row: dict[str, str], article_text: str) -> str:
    return f"""Source lesson page URL:
{row["lesson_url"]}

Deck goal:
Create a Korean high-school data science lesson presentation from the source lesson plan.

Required slide structure:
1. Title and project question
2. Why this civic data problem matters
3. Data and variables students should notice
4. Analysis flow
5. Key chart or evidence
6. Student activity
7. Discussion questions
8. Policy or school action proposal
9. Assessment rubric
10. Wrap-up and source URL

Source lesson content:
{article_text}
"""


def build_payload(args: argparse.Namespace, row: dict[str, str], article_text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "inputText": make_input_text(row, article_text),
        "additionalInstructions": (
            "Use Korean. Make the deck practical for a 50-minute classroom lesson. "
            "Use concise slide text, clear teacher-facing structure, and include the source URL. "
            "If provided image URLs are relevant, use them as chart or evidence visuals."
        ),
        "textMode": args.text_mode,
        "format": "presentation",
        "numCards": args.num_cards,
        "cardSplit": "auto",
        "exportAs": args.export_as,
        "textOptions": {
            "amount": args.text_amount,
            "tone": "clear, teacher-friendly, academic",
            "audience": "Korean high school students and teachers",
            "language": "ko",
        },
        "imageOptions": {"source": args.image_source},
        "cardOptions": {"dimensions": "16x9"},
    }
    if args.theme_id:
        payload["themeId"] = args.theme_id
    if args.folder_id:
        payload["folderIds"] = [args.folder_id]
    return payload


def poll_generation(api_key: str, generation_id: str, args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.time() + args.timeout_seconds
    while True:
        result = http_json(
            "GET",
            f"{API_BASE}/generations/{urllib.parse.quote(generation_id)}",
            api_key=api_key,
            timeout=60,
        )
        status = result.get("status", "")
        print(f"  status={status or 'unknown'}")
        if status in {"completed", "failed"}:
            return result
        if time.time() >= deadline:
            raise TimeoutError(f"Timed out waiting for generation {generation_id}")
        time.sleep(args.poll_interval)


def safe_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:140] or "gamma-presentation"


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "YDSL-Gamma-Queue/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        target.write_bytes(response.read())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sequentially create Gamma decks from lesson URLs.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Input URL CSV.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Result CSV.")
    parser.add_argument("--start", type=int, default=1, help="First project number to process.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of projects to process; 0 means all.")
    parser.add_argument("--force", action="store_true", help="Regenerate rows already marked completed.")
    parser.add_argument("--dry-run", action="store_true", help="Show queue and payload sizes without calling Gamma.")
    parser.add_argument("--num-cards", type=int, default=10, help="Number of Gamma cards/slides.")
    parser.add_argument("--text-mode", choices=["generate", "condense", "preserve"], default="condense")
    parser.add_argument("--text-amount", choices=["brief", "medium", "detailed", "extensive"], default="medium")
    parser.add_argument("--image-source", default="noImages", help="Gamma imageOptions.source value.")
    parser.add_argument("--export-as", choices=["pptx", "pdf", "png"], default="pptx")
    parser.add_argument("--theme-id", default="", help="Optional Gamma theme ID.")
    parser.add_argument("--folder-id", default="", help="Optional Gamma folder ID.")
    parser.add_argument("--api-key-env", default="GAMMA_API_KEY", help="Environment variable containing API key.")
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds.")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Timeout per deck.")
    parser.add_argument("--sleep-seconds", type=int, default=3, help="Pause between projects.")
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR, help="Where to save exported files.")
    parser.add_argument("--no-download", action="store_true", help="Do not download exportUrl files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(args.csv)
    rows = [row for row in rows if int(row["project_no"]) >= args.start]
    if args.limit:
        rows = rows[: args.limit]

    existing = read_existing_results(args.out)
    results = [existing[key] for key in sorted(existing) if key]
    result_by_no = {row.get("project_no", ""): row for row in results}

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not args.dry_run and not api_key:
        print(f"Missing API key. Set ${args.api_key_env} first.", file=sys.stderr)
        return 2

    for row in rows:
        project_no = row["project_no"]
        title = row["title"]
        prior = result_by_no.get(project_no)
        if prior and prior.get("status") == "completed" and not args.force:
            print(f"[{project_no}] skip completed: {title}")
            continue

        print(f"[{project_no}] fetching lesson page: {title}")
        timestamp = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
        result_row = {
            "project_no": project_no,
            "title": title,
            "lesson_url": row["lesson_url"],
            "generation_id": "",
            "status": "pending",
            "gamma_url": "",
            "export_url": "",
            "pptx_path": "",
            "credits_deducted": "",
            "credits_remaining": "",
            "error": "",
            "updated_at": timestamp,
        }
        try:
            article_text = extract_article_text(row["lesson_url"])
            payload = build_payload(args, row, article_text)
            print(f"  extracted={len(article_text):,} chars payload={len(payload['inputText']):,} chars")
            if args.dry_run:
                result_row["status"] = "dry-run"
            else:
                created = http_json("POST", f"{API_BASE}/generations", api_key=api_key, payload=payload)
                generation_id = created["generationId"]
                result_row["generation_id"] = generation_id
                print(f"  generation_id={generation_id}")
                final = poll_generation(api_key, generation_id, args)
                result_row["status"] = final.get("status", "")
                result_row["gamma_url"] = final.get("gammaUrl", "")
                result_row["export_url"] = final.get("exportUrl", "")
                credits = final.get("credits") or {}
                result_row["credits_deducted"] = str(credits.get("deducted", ""))
                result_row["credits_remaining"] = str(credits.get("remaining", ""))
                if final.get("error"):
                    result_row["error"] = json.dumps(final["error"], ensure_ascii=False)
                if (
                    result_row["status"] == "completed"
                    and result_row["export_url"]
                    and not args.no_download
                ):
                    suffix = f".{args.export_as}"
                    target = args.download_dir / f"{project_no}_{safe_filename(title)}{suffix}"
                    download_file(result_row["export_url"], target)
                    result_row["pptx_path"] = str(target.relative_to(ROOT)).replace("\\", "/")
                    print(f"  downloaded={target}")
        except Exception as exc:  # Keep the batch moving.
            result_row["status"] = "failed"
            result_row["error"] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)

        result_by_no[project_no] = result_row
        ordered = [result_by_no[key] for key in sorted(result_by_no)]
        write_results(args.out, ordered)

        if not args.dry_run and args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    print(f"Results: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
