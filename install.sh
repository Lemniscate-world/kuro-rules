#!/bin/bash
# install.sh — Symlink shared AI rules into a target project

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RESET='\033[0m'

RULES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$1"

if [ -z "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Usage: ./install.sh <path-to-project>${RESET}"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Error: Directory '$TARGET_DIR' does not exist.${RESET}"
    exit 1
fi

echo -e "${BLUE}Installing shared rules into: $TARGET_DIR${RESET}"

# Function to link a file
link_file() {
    src="$1"
    dest="$2"
    
    if [ -L "$dest" ]; then
        echo -e "  ${GREEN}✓${RESET} Already linked: $(basename "$dest")"
    elif [ -e "$dest" ]; then
        echo -e "  ${YELLOW}⚠${RESET} Backing up existing $(basename "$dest") to .bak"
        mv "$dest" "$dest.bak"
        ln -s "$src" "$dest"
        echo -e "  ${GREEN}✓${RESET} Linked: $(basename "$dest")"
    else
        ln -s "$src" "$dest"
        echo -e "  ${GREEN}✓${RESET} Linked: $(basename "$dest")"
    fi
}

# Link core files
link_file "$RULES_DIR/AI_GUIDELINES.md" "$TARGET_DIR/AI_GUIDELINES.md"
link_file "$RULES_DIR/.cursorrules" "$TARGET_DIR/.cursorrules"

# Handle pre-commit config (copy instead of link, as projects might need custom hooks)
if [ ! -f "$TARGET_DIR/.pre-commit-config.yaml" ]; then
    echo -e "  ${GREEN}✓${RESET} Copied template: .pre-commit-config.yaml"
    cp "$RULES_DIR/.pre-commit-config.yaml" "$TARGET_DIR/.pre-commit-config.yaml"
else
    echo -e "  ${BLUE}ℹ${RESET} .pre-commit-config.yaml exists, skipping (modify manually)"
fi

# Handle Copilot instructions
mkdir -p "$TARGET_DIR/.github"
link_file "$RULES_DIR/copilot-instructions.md" "$TARGET_DIR/.github/copilot-instructions.md"

echo -e "\n${GREEN}Success!${RESET} Shared rules installed."
echo -e "Remember to add ${YELLOW}.pre-commit-config.yaml${RESET} to git and run ${YELLOW}pre-commit install${RESET}."
