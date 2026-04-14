#!/usr/bin/env bash
set -euo pipefail

# git-whoami.sh
# Checks current repo identity and remote to avoid committing/pushing with wrong account.
#
# Usage:
#   ./scripts/git-whoami.sh
#   ./scripts/git-whoami.sh --strict
#
# Exit codes:
#   0 -> OK / info only
#   2 -> mismatch found in --strict mode

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then
  STRICT=1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[git-whoami] Not inside a git repository."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo '(no-origin)')"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '(unknown)')"

LOCAL_NAME="$(git config --local --get user.name || true)"
LOCAL_EMAIL="$(git config --local --get user.email || true)"
GLOBAL_NAME="$(git config --global --get user.name || true)"
GLOBAL_EMAIL="$(git config --global --get user.email || true)"

ACTIVE_NAME="${LOCAL_NAME:-$GLOBAL_NAME}"
ACTIVE_EMAIL="${LOCAL_EMAIL:-$GLOBAL_EMAIL}"

if [[ -z "$ACTIVE_NAME" ]]; then ACTIVE_NAME="(unset)"; fi
if [[ -z "$ACTIVE_EMAIL" ]]; then ACTIVE_EMAIL="(unset)"; fi

PROFILE="unknown"
EXPECTED_NAME=""
EXPECTED_EMAIL=""

if [[ "$REMOTE_URL" == *"Insu-Health-Design-PR"* || "$REMOTE_URL" == *"adrianinsu"* ]]; then
  PROFILE="work"
  EXPECTED_NAME="AdrianInsu"
  EXPECTED_EMAIL="adrian@insuhealthdesign.com"
elif [[ "$REMOTE_URL" == *"Acordero0369"* || "$REMOTE_URL" == *"Study-with-structure"* ]]; then
  PROFILE="personal"
  EXPECTED_NAME="Adrian Cordero"
  EXPECTED_EMAIL="acordero04@outlook.com"
fi

echo "[git-whoami] repo     : $REPO_ROOT"
echo "[git-whoami] branch   : $BRANCH"
echo "[git-whoami] remote   : $REMOTE_URL"
echo "[git-whoami] profile  : $PROFILE"
echo "[git-whoami] identity : $ACTIVE_NAME <$ACTIVE_EMAIL>"

if [[ -n "$LOCAL_NAME" || -n "$LOCAL_EMAIL" ]]; then
  echo "[git-whoami] source   : local repo config"
else
  echo "[git-whoami] source   : global config"
fi

MISMATCH=0
if [[ "$PROFILE" == "work" ]]; then
  if [[ "$ACTIVE_NAME" != "$EXPECTED_NAME" || "$ACTIVE_EMAIL" != "$EXPECTED_EMAIL" ]]; then
    MISMATCH=1
  fi
elif [[ "$PROFILE" == "personal" ]]; then
  if [[ "$ACTIVE_NAME" != "$EXPECTED_NAME" || "$ACTIVE_EMAIL" != "$EXPECTED_EMAIL" ]]; then
    MISMATCH=1
  fi
fi

if [[ $MISMATCH -eq 1 ]]; then
  echo ""
  echo "[git-whoami] WARNING: identity mismatch for '$PROFILE' repo"
  echo "[git-whoami] expected: $EXPECTED_NAME <$EXPECTED_EMAIL>"
  echo "[git-whoami] current : $ACTIVE_NAME <$ACTIVE_EMAIL>"
  echo ""
  echo "[git-whoami] fix (repo-local):"
  echo "  git config user.name \"$EXPECTED_NAME\""
  echo "  git config user.email \"$EXPECTED_EMAIL\""

  if [[ $STRICT -eq 1 ]]; then
    exit 2
  fi
else
  if [[ "$PROFILE" == "unknown" ]]; then
    echo "[git-whoami] profile unknown: no strict expectation applied."
  else
    echo "[git-whoami] OK: identity matches '$PROFILE' profile."
  fi
fi
