#!/bin/bash
set -euo pipefail

WORKDIR=$(mktemp -d)
OUTDIR="${1:-.}"
trap "rm -rf $WORKDIR" EXIT

echo "[*] Downloading source wordlists..."

# SecLists
SECLISTS="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content"
curl -sL "$SECLISTS/raft-small-directories.txt"    > "$WORKDIR/raft-dirs.txt"
curl -sL "$SECLISTS/raft-small-files.txt"           > "$WORKDIR/raft-files.txt"
curl -sL "$SECLISTS/quickhits.txt"                  > "$WORKDIR/quickhits.txt"
curl -sL "$SECLISTS/common.txt"                     > "$WORKDIR/common.txt"
curl -sL "$SECLISTS/directory-list-2.3-small.txt"   > "$WORKDIR/dirlist-small.txt"
curl -sL "$SECLISTS/Common-DB-Backups.txt"          > "$WORKDIR/db-backups.txt"
curl -sL "$SECLISTS/CGIs.txt"                       > "$WORKDIR/cgis.txt"

# Bo0oM fuzz.txt
curl -sL "https://raw.githubusercontent.com/Bo0oM/fuzz.txt/master/fuzz.txt" > "$WORKDIR/boom-fuzz.txt"

# rix4uni curated lists
curl -sL "https://raw.githubusercontent.com/rix4uni/WordList/main/onelistforshort.txt"   > "$WORKDIR/rix-short.txt"
curl -sL "https://raw.githubusercontent.com/rix4uni/WordList/main/admin-panel-paths.txt" > "$WORKDIR/rix-admin.txt"
curl -sL "https://raw.githubusercontent.com/rix4uni/WordList/main/git-paths.txt"         > "$WORKDIR/rix-git.txt"
curl -sL "https://raw.githubusercontent.com/rix4uni/WordList/main/backup-files.txt"      > "$WORKDIR/rix-backups.txt" || true

echo "[*] Extracting paths from real .gitignore files..."

python3 scripts/extract_gitignore.py > "$WORKDIR/gitignore-paths.txt"

echo "[*] Merging into single wordlist..."

python3 scripts/merge.py "$WORKDIR" "$OUTDIR"

echo "[*] Done!"
wc -l "$OUTDIR/wordlist.txt"
