#!/bin/bash
#
# Content Generation Script
# Quick launcher for generating carousels
#

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR" || exit 1

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Content Generation CLI                        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Usage:"
    echo "  ./generate.sh --account ACCOUNT_NAME [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --account NAME      Account to generate for (required)"
    echo "  --random            Generate random topic from pillars"
    echo "  --topic 'TOPIC'     Generate specific topic"
    echo "  --format FORMAT     habit_list or step_guide"
    echo "  --slides N          Number of slides (5-10)"
    echo "  --count N           Generate N carousels"
    echo "  --verbose           Show detailed output"
    echo ""
    echo "Examples:"
    echo -e "  ${GREEN}# Random carousel${NC}"
    echo "  ./generate.sh --account dreamtimelullabies --random"
    echo ""
    echo -e "  ${GREEN}# Specific topic${NC}"
    echo "  ./generate.sh --account fitness --topic 'leg day workout'"
    echo ""
    echo -e "  ${GREEN}# Batch generation${NC}"
    echo "  ./generate.sh --account cooking --random --count 5"
    echo ""
    echo -e "  ${GREEN}# Step guide with 7 slides${NC}"
    echo "  ./generate.sh --account productivity --topic 'morning routine' --format step_guide --slides 7"
    echo ""
    echo "Available accounts:"
    for account in accounts/*/; do
        if [ -d "$account" ]; then
            account_name=$(basename "$account")
            echo -e "  ${CYAN}• $account_name${NC}"
        fi
    done
    echo ""
    exit 0
fi

# Run the generator
echo ""
echo -e "${CYAN}🎨 Generating content...${NC}"
echo ""

python3 -m cli.generate "$@"

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Generation complete!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Generation failed${NC}"
    echo ""
    exit 1
fi
