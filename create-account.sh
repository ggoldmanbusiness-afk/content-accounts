#!/bin/bash
#
# Content Account Creation Wizard
# Quick launcher script
#

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Content Account Creation Wizard Launcher     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR" || exit 1

# Check if API keys are set
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "   The wizard will prompt you for API keys during step 7"
    echo ""
fi

# Check dependencies
echo -e "${CYAN}Checking dependencies...${NC}"
python3 -c "import questionary, rich" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Missing dependencies. Installing...${NC}"
    pip3 install questionary rich
    echo ""
fi

echo -e "${GREEN}✓ Ready to create your account!${NC}"
echo ""
echo -e "${CYAN}This wizard will take approximately 25-30 minutes${NC}"
echo -e "${CYAN}and will guide you through 9 steps:${NC}"
echo ""
echo "  1. Account Identity"
echo "  2. Brand Voice"
echo "  3. Content Pillars (templates available!)"
echo "  4. Visual Style (color presets available!)"
echo "  5. Hashtag Strategy"
echo "  6. Output Configuration"
echo "  7. API Keys"
echo "  8. Review & Confirm"
echo "  9. Generate Sample Carousels"
echo ""
echo -e "${GREEN}Press Enter to start, or Ctrl+C to cancel...${NC}"
read -r

# Run the wizard
python3 -m cli.create_account

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Account Created Successfully! 🎉              ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Generate content:"
    echo -e "     ${CYAN}./generate.sh --account YOURACCOUNTNAME --random${NC}"
    echo ""
    echo "  2. Customize your account:"
    echo -e "     ${CYAN}cd accounts/YOURACCOUNTNAME${NC}"
    echo -e "     ${CYAN}nano config.py${NC}"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠️  Wizard cancelled or encountered an error${NC}"
    echo ""
fi
