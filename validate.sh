#!/bin/bash
#
# Account Validation Script
# Validates account configurations
#

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR" || exit 1

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Account Configuration Validator               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# If no arguments, validate all
if [ $# -eq 0 ]; then
    echo "Validating all accounts..."
    echo ""
    python3 -m cli.validate --all
else
    python3 -m cli.validate "$@"
fi

echo ""
