"""Regenerate the auto-managed sections of the profile README.

Sections are delimited by `<!-- AUTO:<NAME>:START -->` / `<!-- AUTO:<NAME>:END -->`
markers. Everything outside the markers is left untouched.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "AmirKenzo")
README = Path(__file__).resolve().parents[2] / "README.md"
API = "https://api.github.com"

FEATURED_COUNT = 6
CURRENTLY_COUNT = 2
STACK_LANG_COUNT = 4

# Only the profile repo itself is hidden; every other owned repo is eligible.
EXCLUDED_REPOS = {USERNAME.lower()}

# GitHub language / repo topic -> skillicons.dev id. Unknown names are ignored.
LANGUAGE_ICONS = {
    "Python": "python",
    "TypeScript": "ts",
    "JavaScript": "js",
    "Rust": "rust",
    "Go": "go",
    "Shell": "bash",
    "PowerShell": "powershell",
    "HTML": "html",
    "CSS": "css",
    "SCSS": "sass",
    "Vue": "vue",
    "Svelte": "svelte",
    "Dockerfile": "docker",
    "C": "c",
    "C++": "cpp",
    "C#": "cs",
    "Java": "java",
    "Kotlin": "kotlin",
    "Dart": "dart",
    "Swift": "swift",
    "PHP": "php",
    "Lua": "lua",
    "Ruby": "ruby",
}
TOPIC_ICONS = {
    "docker": "docker",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "react": "react",
    "nextjs": "nextjs",
    "vite": "vite",
    "tailwindcss": "tailwind",
    "nodejs": "nodejs",
    "electron": "electron",
    "tauri": "tauri",
    "flutter": "flutter",
    "postgresql": "postgres",
    "redis": "redis",
    "mongodb": "mongodb",
    "sqlite": "sqlite",
    "mysql": "mysql",
    "discord": "discord",
    "discord-bot": "discord",
    "cloudflare": "cloudflare",
}
BASE_ICONS = ["linux", "git", "githubactions"]

PIN_CARD = (
    '  <a href="https://github.com/{user}/{repo}">'
    '<img src="https://github-readme-stats.vercel.app/api/pin/?username={user}&repo={repo}'
    '&theme=chartreuse-dark&hide_border=true&bg_color=0d1117&title_color=00ff88" /></a>'
)


def api_get(path: str) -> Any:
    request = urllib.request.Request(
        f"{API}{path}", headers={"Accept": "application/vnd.github+json"}
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_repos() -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = api_get(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            return [r for r in repos if not r["fork"]]
        page += 1


def language_totals(repos: list[dict[str, Any]]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for repo in repos:
        totals.update(api_get(f"/repos/{repo['full_name']}/languages"))
    return totals


def replace_section(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- AUTO:{name}:START -->\n).*?(\n<!-- AUTO:{name}:END -->)", re.DOTALL
    )
    if not pattern.search(text):
        raise ValueError(f"Markers for section {name!r} not found in README")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def replace_field(text: str, field: str, value: list[str]) -> str:
    """Rewrite one `field = [...]` line inside the WHOAMI block, keeping its alignment."""
    pattern = re.compile(rf"^(\s*{field}\s*=\s*).*$", re.MULTILINE)
    return pattern.sub(
        lambda m: m.group(1) + json.dumps(value, ensure_ascii=False), text, count=1
    )


def build(text: str) -> str:
    repos = fetch_repos()
    visible = [r for r in repos if r["name"].lower() not in EXCLUDED_REPOS]

    langs = [lang for lang, _ in language_totals(repos).most_common()]
    icons: list[str] = []
    topics = [t for r in repos for t in r.get("topics", [])]
    for icon in (
        [LANGUAGE_ICONS.get(lang) for lang in langs]
        + [TOPIC_ICONS.get(t) for t in topics]
        + BASE_ICONS
    ):
        if icon and icon not in icons:
            icons.append(icon)
    stack_html = f'  <img src="https://skillicons.dev/icons?i={",".join(icons)}&perline=7&theme=dark" />'
    text = replace_section(text, "STACK", stack_html)

    featured = sorted(
        visible, key=lambda r: (r["stargazers_count"], r["pushed_at"]), reverse=True
    )
    cards = [
        PIN_CARD.format(user=USERNAME, repo=r["name"])
        for r in featured[:FEATURED_COUNT]
    ]
    text = replace_section(text, "PROJECTS", "\n".join(cards))

    active = [r for r in visible if not r["archived"]]
    recent = sorted(active, key=lambda r: r["pushed_at"], reverse=True)
    whoami = re.search(
        r"<!-- AUTO:WHOAMI:START -->\n(.*?)\n<!-- AUTO:WHOAMI:END -->", text, re.DOTALL
    )
    if not whoami:
        raise ValueError("Markers for section 'WHOAMI' not found in README")
    block = replace_field(
        whoami.group(1),
        "stack",
        [lang for lang in langs if lang in LANGUAGE_ICONS][:STACK_LANG_COUNT],
    )
    block = replace_field(
        block, "currently", [r["name"] for r in recent[:CURRENTLY_COUNT]]
    )
    return replace_section(text, "WHOAMI", block)


def main() -> int:
    original = README.read_text(encoding="utf-8")
    updated = build(original)
    if updated == original:
        print("README already up to date")
        return 0
    README.write_text(updated, encoding="utf-8")
    print("README updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
