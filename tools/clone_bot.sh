#!/usr/bin/env bash
# Clone a bot repository and run initial secret scanning.
#
# Two-stage security gate:
#   Stage 1 (hard): grep for private key patterns — delete clone on match
#   Stage 2 (soft): run scan_secrets.py — report findings, keep clone
#
# Usage:
#   ./tools/clone_bot.sh <repo-url> <bot-name>
#
# Example:
#   ./tools/clone_bot.sh https://github.com/chainstacklabs/hyperliquid-grid-trading-bot chainstack-grid-bot

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BOTS_DIR="$PROJECT_DIR/bots"
EVAL_DIR="$PROJECT_DIR/evaluations"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <repo-url> <bot-name>"
    echo ""
    echo "  repo-url   Git repository URL to clone"
    echo "  bot-name   Short name for the bot (used as directory name)"
    echo ""
    echo "Example:"
    echo "  $0 https://github.com/user/bot my-bot"
    exit 1
}

# Validate arguments
if [ $# -ne 2 ]; then
    usage
fi

REPO_URL="$1"
BOT_NAME="$2"
BOT_DIR="$BOTS_DIR/$BOT_NAME"
BOT_EVAL_DIR="$EVAL_DIR/$BOT_NAME"

# Check target doesn't already exist
if [ -d "$BOT_DIR" ]; then
    echo -e "${RED}Error: $BOT_DIR already exists. Remove it first or choose a different name.${NC}"
    exit 1
fi

# Create directories
mkdir -p "$BOTS_DIR"
mkdir -p "$BOT_EVAL_DIR"

echo "=== Cloning $REPO_URL into $BOT_DIR ==="

# Shallow clone
if ! git clone --depth 1 "$REPO_URL" "$BOT_DIR" 2>&1; then
    echo -e "${RED}Error: git clone failed${NC}"
    exit 1
fi

echo ""
echo "=== Stage 1: Hard gate — private key pattern scan ==="

# Stage 1: Fast grep for 64-char hex strings (potential private keys)
# This is the hard gate — match = delete clone immediately
KEY_MATCHES=$(grep -rn '0x[a-fA-F0-9]\{64\}' "$BOT_DIR" --include='*.py' --include='*.js' --include='*.ts' --include='*.rs' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.toml' --include='*.env' --include='*.cfg' --include='*.ini' --include='*.txt' 2>/dev/null || true)

if [ -n "$KEY_MATCHES" ]; then
    echo -e "${RED}CRITICAL: Potential private key(s) found!${NC}"
    echo ""
    echo "$KEY_MATCHES"
    echo ""
    echo -e "${RED}Deleting clone for safety.${NC}"
    rm -rf "$BOT_DIR"
    exit 2
fi

echo -e "${GREEN}Stage 1 passed: no private key patterns found.${NC}"

echo ""
echo "=== Stage 2: Soft gate — full secret scan ==="

# Stage 2: Run scan_secrets.py for comprehensive scanning
SCAN_OUTPUT="$BOT_EVAL_DIR/secret-scan-initial.json"

if python "$SCRIPT_DIR/scan_secrets.py" "$BOT_DIR" --output "$SCAN_OUTPUT"; then
    echo -e "${GREEN}Stage 2 passed: no critical findings.${NC}"
else
    echo -e "${YELLOW}Stage 2: findings detected (see $SCAN_OUTPUT for details).${NC}"
    echo -e "${YELLOW}Clone kept for manual review.${NC}"
fi

echo ""
echo "=== Clone complete ==="
echo "Bot source:    $BOT_DIR"
echo "Scan results:  $SCAN_OUTPUT"
echo "Next step:     python tools/audit_deps.py $BOT_DIR"
