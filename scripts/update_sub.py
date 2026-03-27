#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UPSTREAM_BLOB_URL = "https://github.com/free-nodes/v2rayfree/blob/main/README.md"
UPSTREAM_CONTENTS_API_URL = (
    "https://api.github.com/repos/free-nodes/v2rayfree/contents/README.md?ref=main"
)
TARGET_HEADING = "v2ray免费节点分享"
API_VERSION = "2022-11-28"
REQUEST_TIMEOUT_SECONDS = 30

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "sub.txt"

HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
FENCE_RE = re.compile(r"^(```+|~~~+)")
NODE_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$")


def log(message: str) -> None:
    print(f"[update_sub] {message}")


def build_request() -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "sub-sync/1.0",
        "X-GitHub-Api-Version": API_VERSION,
    }

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return urllib.request.Request(UPSTREAM_CONTENTS_API_URL, headers=headers)


def fetch_upstream_readme() -> str:
    request = build_request()
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", None)
            if status and status != 200:
                raise RuntimeError(f"unexpected upstream status: {status}")

            charset = response.headers.get_content_charset() or "utf-8"
            markdown = response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"failed to fetch upstream README: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch upstream README: {exc.reason}") from exc

    if not markdown.strip():
        raise RuntimeError("upstream README response was empty")

    log(f"Fetched upstream README via GitHub Contents API for {UPSTREAM_BLOB_URL}")
    return markdown


def strip_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)

    while start < end and not lines[start].strip():
        start += 1

    while end > start and not lines[end - 1].strip():
        end -= 1

    return lines[start:end]


def extract_heading_section(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    target_index: int | None = None
    target_level: int | None = None

    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue

        heading_text = match.group(2).strip()
        if heading_text == TARGET_HEADING:
            target_index = index
            target_level = len(match.group(1))
            break

    if target_index is None or target_level is None:
        raise RuntimeError(f"failed to locate heading: {TARGET_HEADING}")

    end_index = len(lines)
    for index in range(target_index + 1, len(lines)):
        match = HEADING_RE.match(lines[index])
        if match and len(match.group(1)) <= target_level:
            end_index = index
            break

    section_lines = strip_blank_edges(lines[target_index + 1 : end_index])
    if not section_lines:
        raise RuntimeError(f"heading '{TARGET_HEADING}' exists but its section is empty")

    return section_lines


def extract_node_lines(section_lines: list[str]) -> list[str]:
    content_lines = section_lines
    fence_match = FENCE_RE.match(section_lines[0].strip())

    if fence_match:
        fence_token = fence_match.group(1)
        closing_index = None
        for index, line in enumerate(section_lines[1:], start=1):
            if line.strip().startswith(fence_token[0] * len(fence_token)):
                closing_index = index
                break

        if closing_index is None:
            content_lines = section_lines[1:]
        else:
            content_lines = section_lines[1:closing_index]

    normalized_lines = [line.strip() for line in content_lines if line.strip()]
    node_lines = [line for line in normalized_lines if NODE_URI_RE.match(line)]

    if not node_lines:
        raise RuntimeError("no valid node URIs were extracted from the target section")

    return node_lines


def write_sub_file(node_lines: list[str]) -> bool:
    new_content = "\n".join(node_lines) + "\n"
    current_content = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else None

    if current_content == new_content:
        log(f"{OUTPUT_PATH.name} is already up to date ({len(node_lines)} node lines)")
        return False

    temp_path = OUTPUT_PATH.with_suffix(".txt.tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(new_content)
    temp_path.replace(OUTPUT_PATH)

    log(f"Updated {OUTPUT_PATH.name} with {len(node_lines)} node lines")
    return True


def main() -> int:
    try:
        markdown = fetch_upstream_readme()
        section_lines = extract_heading_section(markdown)
        node_lines = extract_node_lines(section_lines)
        write_sub_file(node_lines)
    except Exception as exc:  # noqa: BLE001 - single-process script with explicit logging
        log(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
