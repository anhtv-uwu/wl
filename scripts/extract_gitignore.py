#!/usr/bin/env python3
"""Extract web-fuzzable paths from REAL .gitignore files on GitHub.

Uses GitHub Code Search API to find actual .gitignore files from real repos,
not just templates. This gives us paths developers ACTUALLY use in production.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Search queries to find diverse .gitignore files across tech stacks
SEARCH_QUERIES = [
    # Web frameworks
    "filename:.gitignore node_modules dist",
    "filename:.gitignore vendor public storage",
    "filename:.gitignore __pycache__ venv",
    "filename:.gitignore target build gradle",
    "filename:.gitignore .next .nuxt",
    "filename:.gitignore wp-content uploads",
    "filename:.gitignore .terraform tfstate",
    "filename:.gitignore .env secret",
    "filename:.gitignore coverage htmlcov",
    "filename:.gitignore bower_components",
    "filename:.gitignore .angular dist",
    "filename:.gitignore Pods Carthage",
    "filename:.gitignore .serverless amplify",
    "filename:.gitignore docker-compose",
    "filename:.gitignore firebase .firebase",
]

# Also fetch from GitHub's official templates repo
TEMPLATE_NAMES = [
    "Node", "Python", "Java", "Go", "Ruby", "Rust", "Android", "Angular",
    "CakePHP", "Drupal", "Laravel", "Magento", "Rails", "Symfony",
    "WordPress", "Terraform", "Flutter", "Elixir", "Scala", "Kotlin",
    "Swift", "Dart", "Haskell",
]

# Also fetch from gitignore.io / toptal collection
GITIGNORE_IO_TEMPLATES = [
    "node", "python", "django", "flask", "java", "maven", "gradle",
    "go", "ruby", "rails", "rust", "android", "angular", "react",
    "vue", "nuxt", "next", "svelte", "laravel", "symfony", "wordpress",
    "drupal", "magento", "terraform", "docker", "dotenv",
    "firebase", "unity", "unrealengine",
]


def github_search(query, per_page=30):
    """Search GitHub for .gitignore files and return their content URLs."""
    url = f"https://api.github.com/search/code?q={urllib.request.quote(query)}&per_page={per_page}"
    headers = {
        "User-Agent": "wordlist-builder",
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return [item.get("url", "") for item in data.get("items", [])]
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  Rate limited, sleeping 60s...", file=sys.stderr)
            time.sleep(60)
            return []
        print(f"  Search error: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  Search error: {e}", file=sys.stderr)
        return []


def fetch_content(api_url):
    """Fetch file content from GitHub API."""
    try:
        import base64
        headers = {
            "User-Agent": "wordlist-builder",
            "Accept": "application/vnd.github.v3+json",
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        req = urllib.request.Request(api_url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("encoding") == "base64" and data.get("content"):
            return base64.b64decode(data["content"]).decode(errors="replace")
    except Exception:
        pass
    return ""


def fetch_template(name):
    """Fetch from GitHub's official gitignore templates."""
    url = f"https://api.github.com/repos/github/gitignore/contents/{name}.gitignore"
    return fetch_content(url)


def fetch_gitignoreio(name):
    """Fetch from gitignore.io (toptal)."""
    url = f"https://www.toptal.com/developers/gitignore/api/{name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wordlist-builder"})
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.read().decode(errors="replace")
    except Exception:
        return ""


def extract_paths(content):
    """Extract fuzzable paths from .gitignore content."""
    paths = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        path = line.lstrip("/").rstrip("/")

        # Skip pure wildcard-only patterns (*.log, *.pyc)
        if re.match(r"^\*\.\w+$", path):
            continue
        if len(path) <= 1 or re.match(r"^[\*\?\[\]]+$", path):
            continue
        if path.startswith("*") and "/" not in path:
            continue

        # Clean up globs
        path = re.sub(r"/?\*\*/?", "", path)
        path = re.sub(r"/?\*$", "", path)
        path = path.strip("/")

        if path and len(path) > 1:
            # Skip binary extensions
            if re.match(r".*\.(pyc|pyo|class|o|so|dll|exe|jar|war|a|lib|obj)$", path):
                continue
            paths.add(path)
            # Add parent dirs
            if "/" in path:
                parent = path.rsplit("/", 1)[0]
                if parent and len(parent) > 1:
                    paths.add(parent)

    return paths


def main():
    all_paths = set()

    # Source 1: GitHub official templates
    print("[1/3] Fetching GitHub official templates...", file=sys.stderr)
    for name in TEMPLATE_NAMES:
        content = fetch_template(name)
        if content:
            paths = extract_paths(content)
            all_paths.update(paths)
            print(f"  [{name}] -> {len(paths)} paths", file=sys.stderr)
        time.sleep(0.5)  # Rate limit

    # Source 2: gitignore.io templates (broader coverage)
    print("[2/3] Fetching gitignore.io templates...", file=sys.stderr)
    for name in GITIGNORE_IO_TEMPLATES:
        content = fetch_gitignoreio(name)
        if content:
            paths = extract_paths(content)
            all_paths.update(paths)
            print(f"  [gitignore.io/{name}] -> {len(paths)} paths", file=sys.stderr)
        time.sleep(0.3)

    # Source 3: Real .gitignore files from GitHub search (no auth = limited)
    print("[3/3] Searching real .gitignore files on GitHub...", file=sys.stderr)
    fetched_urls = set()
    for query in SEARCH_QUERIES:
        urls = github_search(query, per_page=10)
        for url in urls:
            if url in fetched_urls:
                continue
            fetched_urls.add(url)
            content = fetch_content(url)
            if content:
                paths = extract_paths(content)
                all_paths.update(paths)
        print(f"  [{query[:40]}...] -> {len(urls)} files", file=sys.stderr)
        time.sleep(2)  # GitHub rate limit (unauthenticated)

    # Extra well-known paths
    extra = {
        ".env", ".env.local", ".env.production", ".env.staging",
        ".env.development", ".env.backup", ".env.old", ".env.bak",
        ".env.example", ".env.sample", ".env.test",
        "dist", "build", "out", "output", ".next", ".nuxt", ".angular",
        "public/build", "public/storage", "public/hot",
        "node_modules", "vendor", "bower_components", "packages",
        ".cache", ".parcel-cache", ".turbo", "__pycache__",
        "coverage", "htmlcov", ".coverage", ".nyc_output",
        "logs", "log", "tmp", "temp",
        "storage", "storage/logs", "storage/framework", "storage/app",
        "bootstrap/cache", "bootstrap/compiled.php",
        "config/database.yml", "config/secrets.yml",
        "config/master.key", "config/credentials.yml.enc",
        ".terraform", "terraform.tfstate", "terraform.tfstate.backup",
        "terraform.tfvars", ".serverless", ".aws-sam",
        "secrets.yaml", "secrets.yml", "secrets.json",
        ".firebase", ".amplify", "amplify/team-provider-info.json",
        "db.sqlite3", "database.sqlite",
        "local.properties", "google-services.json",
        ".idea", ".vscode", ".vscode/settings.json",
    }
    all_paths.update(extra)

    # Output
    for path in sorted(all_paths):
        print(path)

    print(f"\n  Total: {len(all_paths)} unique paths from gitignore", file=sys.stderr)


if __name__ == "__main__":
    main()
