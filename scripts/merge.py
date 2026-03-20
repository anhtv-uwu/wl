#!/usr/bin/env python3
"""Merge all wordlist sources into a single deduplicated wordlist."""

import os
import re
import sys

WORKDIR = sys.argv[1]
OUTDIR = sys.argv[2]

# Custom high-value paths (from real bug bounty findings)
CUSTOM_CONFIG = """
config.json
configuration.json
settings.json
configs.json
conf.json
app.config.json
application.json
config.prod.json
config.production.json
config.dev.json
config.development.json
config.staging.json
config.test.json
config.local.json
config/config.json
config/default.json
config/prod.json
config/production.json
config/development.json
config/app.json
app/config.json
src/config.json
assets/config.json
assets/config.production.json
assets/configs.json
static/config.json
public/config.json
dist/config.json
js/config.json
api/config.json
api/v1/config.json
api/v2/config.json
apiconfig.json
credentials/config.json
secrets/config.json
secret/config.json
keys/config.json
auth/config.json
aws/config.json
aws/credentials.json
cloud/config.json
s3/config.json
db/config.json
database/config.json
mysql/config.json
postgres/config.json
mongodb/config.json
.env
.env.local
.env.production
.env.staging
.env.development
.env.backup
.env.old
.env.bak
.env.example
.env.sample
.env.test
.git/config
.git/HEAD
.git/index
.git/logs/HEAD
.gitignore
.svn/entries
.svn/wc.db
.htaccess
.htpasswd
.DS_Store
.vscode/settings.json
.vscode/launch.json
package.json
package-lock.json
composer.json
composer.lock
Gemfile
Gemfile.lock
yarn.lock
pnpm-lock.yaml
webpack.config.js
tsconfig.json
angular.json
vue.config.js
next.config.js
nuxt.config.js
firebase.json
firebaseConfig.json
serviceAccountKey.json
google-services.json
appsettings.json
appsettings.Development.json
appsettings.Production.json
web.config
wp-config.php
wp-config.php.bak
wp-config.php.old
wp-config.txt
phpinfo.php
info.php
test.php
server-status
server-info
elmah.axd
trace.axd
swagger.json
swagger.yaml
swagger-ui.html
openapi.json
openapi.yaml
.well-known/openapi.json
.well-known/security.txt
graphql
graphiql
api/graphql
actuator
actuator/env
actuator/health
actuator/info
actuator/mappings
actuator/configprops
actuator/beans
actuator/metrics
_profiler
_debugbar
debug
debug/default/view
.aws/credentials
.docker/config.json
.kube/config
terraform.tfstate
terraform.tfvars
Dockerfile
docker-compose.yml
docker-compose.yaml
Vagrantfile
Jenkinsfile
.circleci/config.yml
.github/workflows
.gitlab-ci.yml
bitbucket-pipelines.yml
api
api/v1
api/v2
api/v3
api/users
api/admin
api/auth
api/login
api/token
api/me
api/profile
api/settings
api/config
api/health
api/status
api/info
api/debug
api/internal
api/private
api/docs
api/swagger
api/webhooks
api/upload
api/export
api/download
api/search
api/proxy
api/callback
build
phpmyadmin
phpMyAdmin
clientaccesspolicy.xml
"""

# Bad patterns to filter out (noise, not useful)
BAD_PATTERNS = re.compile(
    r"^[0-9]+$"           # pure numbers
    r"|^[0-9a-f]{32,}$"   # hex hashes
    r"|^\s*$"              # empty
    r"|^#"                 # comments
    r"|[\x00-\x1f]"       # control chars
)


def load_file(path):
    """Load a wordlist file, clean entries."""
    entries = []
    try:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                # Strip leading /
                line = line.lstrip("/")
                if not line:
                    continue
                if BAD_PATTERNS.match(line):
                    continue
                entries.append(line)
    except FileNotFoundError:
        print(f"  [WARN] {path} not found, skipping", file=sys.stderr)
    return entries


def main():
    seen = set()  # lowercase dedup
    result = []   # ordered, original case preserved for dotfiles

    def add_entries(entries, label):
        added = 0
        for entry in entries:
            key = entry.lower()
            if key not in seen:
                seen.add(key)
                result.append(entry)
                added += 1
        print(f"  [{label}] +{added} new (total: {len(result)})", file=sys.stderr)

    # Priority 1: Custom high-value paths
    custom = [l.strip() for l in CUSTOM_CONFIG.strip().split("\n") if l.strip()]
    add_entries(custom, "custom-bugbounty")

    # Priority 2: gitignore paths
    gi_path = os.path.join(WORKDIR, "gitignore-paths.txt")
    add_entries(load_file(gi_path), "gitignore")

    # Priority 3: quickhits (curated)
    add_entries(load_file(os.path.join(WORKDIR, "quickhits.txt")), "quickhits")

    # Priority 4: Bo0oM fuzz.txt (curated)
    add_entries(load_file(os.path.join(WORKDIR, "boom-fuzz.txt")), "boom-fuzz")

    # Priority 5: rix4uni curated (cap large files)
    MAX_PER_SOURCE = {
        "rix-backups.txt": 5000,  # 286K entries, take top 5K only
    }
    for name in ["rix-short.txt", "rix-admin.txt", "rix-git.txt", "rix-backups.txt"]:
        path = os.path.join(WORKDIR, name)
        entries = load_file(path)
        cap = MAX_PER_SOURCE.get(name)
        if cap and len(entries) > cap:
            entries = entries[:cap]
        add_entries(entries, name)

    # Priority 6: common.txt
    add_entries(load_file(os.path.join(WORKDIR, "common.txt")), "common")

    # Priority 7: raft-small-directories
    add_entries(load_file(os.path.join(WORKDIR, "raft-dirs.txt")), "raft-dirs")

    # Priority 8: raft-small-files
    add_entries(load_file(os.path.join(WORKDIR, "raft-files.txt")), "raft-files")

    # Priority 9: DB backups + CGIs
    add_entries(load_file(os.path.join(WORKDIR, "db-backups.txt")), "db-backups")
    add_entries(load_file(os.path.join(WORKDIR, "cgis.txt")), "cgis")

    # Priority 10: Fill from directory-list-2.3-small (large source)
    dirlist = load_file(os.path.join(WORKDIR, "dirlist-small.txt"))
    # Filter low-quality entries from dirlist
    filtered = [e for e in dirlist if len(e) > 2 and not re.match(r"^[0-9_\-]+$", e)]
    add_entries(filtered, "dirlist-2.3-small")

    # Write single merged wordlist
    out_main = os.path.join(OUTDIR, "wordlist.txt")
    with open(out_main, "w") as f:
        for entry in result:
            f.write(entry + "\n")

    print(f"\n[*] Final: {len(result)} entries in wordlist.txt", file=sys.stderr)


if __name__ == "__main__":
    main()
