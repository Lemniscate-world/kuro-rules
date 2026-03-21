#!/bin/bash
# install.sh - Install shared AI rules and research scaffold into a target project

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RESET='\033[0m'

RULES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-}"

if [ -z "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Usage: ./install.sh <path-to-project>${RESET}"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Error: Directory '$TARGET_DIR' does not exist.${RESET}"
    exit 1
fi

PROJECT_NAME="$(basename "$TARGET_DIR")"
TODAY="$(date +%F)"

PRIMARY_GEO="TBD"
TARGET_USER="TBD"
BUYER="TBD"
PAIN_POINT="TBD"
PRODUCT_WEDGE="TBD"
ALTERNATIVES="TBD"
VALIDATION_STAGE="L0"
IN_SCOPE="TBD"
OUT_OF_SCOPE="TBD"
CLAIM="TBD"
WHAT_IT_PROVES="TBD"
OPEN_QUESTION="TBD"
QUESTION_1="What is the highest-confidence pain point for this project?"
WHY_1="The wedge is undefined until the operational pain is precise."
HOW_1="Run desk research and 3-5 expert calls."
STAGE_1="L0 -> L1"
QUESTION_2="Who owns the budget and approval path?"
WHY_2="A problem without a buyer is not enough."
HOW_2="Interview likely operators, buyers, and integrators."
STAGE_2="L1 -> L2"
QUESTION_3="Can the first pilot avoid heavy integration or compliance work?"
WHY_3="Pilot friction determines speed to first contract."
HOW_3="Map current workflow and minimum required controls."
STAGE_3="L2 -> L3"

apply_project_defaults() {
    case "$PROJECT_NAME" in
        Iroko)
            PRIMARY_GEO="Togo"
            TARGET_USER="tier-2 banks and MFIs"
            BUYER="head of operations, digital banking, or support"
            PAIN_POINT="customer-support and self-service workflows are expensive, fragile, and pressured by digital migration"
            PRODUCT_WEDGE="white-label banking workflow for support, self-care, human handoff, and audit trail"
            ALTERNATIVES="Semoa, internal teams, integrators, call center plus branch"
            VALIDATION_STAGE="L1"
            IN_SCOPE="support, self-care, human handoff, audit trail"
            OUT_OF_SCOPE="bot-initiated payments, full KYC, open general AI assistant"
            CLAIM="there may still be a narrow banking-workflow wedge beyond generic WhatsApp Banking"
            WHAT_IT_PROVES="digital pressure exists, but the anti-incumbent wedge is still unproven"
            OPEN_QUESTION="is there a sellable wedge beyond Semoa and internal workflows?"
            QUESTION_1="Is there a sellable Iroko wedge beyond Semoa?"
            WHY_1="Without a clear wedge, the project is category demand without startup space."
            HOW_1="Interview banks, MFIs, BSPs, and integrators."
            STAGE_1="L1 -> L2"
            QUESTION_2="What deterministic WhatsApp workflow remains compliant and acceptable?"
            WHY_2="Platform and compliance boundaries define the real product."
            HOW_2="Confirm policy and operating constraints with BSPs and compliance owners."
            STAGE_2="L1 -> L2"
            QUESTION_3="Can a pilot start without deep payment-core integration?"
            WHY_3="Heavy integration kills the first contract."
            HOW_3="Map the narrowest workflow that still creates ROI."
            STAGE_3="L2 -> L3"
            ;;
        Kapok)
            PRIMARY_GEO="Togo"
            TARGET_USER="insurers and claims operations teams"
            BUYER="head of claims, operations, CIO, or digital lead"
            PAIN_POINT="claims intake, document collection, and status follow-up are slow, manual, and hard to audit"
            PRODUCT_WEDGE="claims ops SaaS for first notice of loss, document capture, completeness checks, expert queue, status tracking, and fraud flags"
            ALTERNATIVES="email plus Excel, core-insurance modules, brokers, TPAs, internal teams"
            VALIDATION_STAGE="L1"
            IN_SCOPE="first notice of loss, document capture, completeness checklist, expert queue, status tracking, fraud flags"
            OUT_OF_SCOPE="underwriting, pricing, policy administration, generic AI chatbot"
            CLAIM="claims workflow pressure creates a cleaner first wedge than generic insurtech messaging"
            WHAT_IT_PROVES="claims-process pain is recent and operational, but buyer and integration proof still require calls"
            OPEN_QUESTION="can a narrow pilot start without replacing the insurer core?"
            QUESTION_1="Who owns the budget for claims workflow improvement?"
            WHY_1="Budget ownership determines whether the project is sellable."
            HOW_1="Interview claims leads, operations leads, and CIOs."
            STAGE_1="L1 -> L2"
            QUESTION_2="Which claims line is the best first wedge?"
            WHY_2="The first pilot must be narrow enough to show ROI quickly."
            HOW_2="Compare document defects, delays, and volume by claims line."
            STAGE_2="L2 -> L3"
            QUESTION_3="What minimum controls are mandatory for a pilot?"
            WHY_3="Compliance scope sets the real build cost."
            HOW_3="Validate with insurer IT, compliance, and local integrators."
            STAGE_3="L2 -> L3"
            ;;
    esac
}

render_template() {
    local src="$1"
    local dest="$2"
    mkdir -p "$(dirname "$dest")"

    sed \
        -e "s|{{DATE}}|$TODAY|g" \
        -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
        -e "s|{{PRIMARY_GEO}}|$PRIMARY_GEO|g" \
        -e "s|{{TARGET_USER}}|$TARGET_USER|g" \
        -e "s|{{BUYER}}|$BUYER|g" \
        -e "s|{{PAIN_POINT}}|$PAIN_POINT|g" \
        -e "s|{{PRODUCT_WEDGE}}|$PRODUCT_WEDGE|g" \
        -e "s|{{ALTERNATIVES}}|$ALTERNATIVES|g" \
        -e "s|{{VALIDATION_STAGE}}|$VALIDATION_STAGE|g" \
        -e "s|{{IN_SCOPE}}|$IN_SCOPE|g" \
        -e "s|{{OUT_OF_SCOPE}}|$OUT_OF_SCOPE|g" \
        -e "s|{{CLAIM}}|$CLAIM|g" \
        -e "s|{{WHAT_IT_PROVES}}|$WHAT_IT_PROVES|g" \
        -e "s|{{OPEN_QUESTION}}|$OPEN_QUESTION|g" \
        -e "s|{{QUESTION_1}}|$QUESTION_1|g" \
        -e "s|{{WHY_1}}|$WHY_1|g" \
        -e "s|{{HOW_1}}|$HOW_1|g" \
        -e "s|{{STAGE_1}}|$STAGE_1|g" \
        -e "s|{{QUESTION_2}}|$QUESTION_2|g" \
        -e "s|{{WHY_2}}|$WHY_2|g" \
        -e "s|{{HOW_2}}|$HOW_2|g" \
        -e "s|{{STAGE_2}}|$STAGE_2|g" \
        -e "s|{{QUESTION_3}}|$QUESTION_3|g" \
        -e "s|{{WHY_3}}|$WHY_3|g" \
        -e "s|{{HOW_3}}|$HOW_3|g" \
        -e "s|{{STAGE_3}}|$STAGE_3|g" \
        -e "s|{{SOURCE_URL}}|TBD|g" \
        -e "s|{{SOURCE_DATE}}|$TODAY|g" \
        "$src" > "$dest"
}

link_file() {
    local src="$1"
    local dest="$2"

    mkdir -p "$(dirname "$dest")"

    if [ -L "$dest" ]; then
        echo -e "  ${GREEN}OK${RESET} Already linked: $(basename "$dest")"
    elif [ -e "$dest" ]; then
        echo -e "  ${YELLOW}WARN${RESET} Backing up existing $(basename "$dest") to .bak"
        mv "$dest" "$dest.bak"
        ln -s "$src" "$dest"
        echo -e "  ${GREEN}OK${RESET} Linked: $(basename "$dest")"
    else
        ln -s "$src" "$dest"
        echo -e "  ${GREEN}OK${RESET} Linked: $(basename "$dest")"
    fi
}

copy_if_missing() {
    local src="$1"
    local dest="$2"

    mkdir -p "$(dirname "$dest")"

    if [ -e "$dest" ]; then
        echo -e "  ${BLUE}INFO${RESET} Exists, skipping: ${dest#$TARGET_DIR/}"
    else
        cp "$src" "$dest"
        echo -e "  ${GREEN}OK${RESET} Copied: ${dest#$TARGET_DIR/}"
    fi
}

render_if_missing() {
    local src="$1"
    local dest="$2"

    if [ -e "$dest" ]; then
        echo -e "  ${BLUE}INFO${RESET} Exists, skipping: ${dest#$TARGET_DIR/}"
    else
        render_template "$src" "$dest"
        echo -e "  ${GREEN}OK${RESET} Created: ${dest#$TARGET_DIR/}"
    fi
}

cleanup_legacy_root_copilot() {
    local root_copy="$TARGET_DIR/copilot-instructions.md"
    local github_copy="$TARGET_DIR/.github/copilot-instructions.md"

    if [ -e "$root_copy" ] && [ -e "$github_copy" ]; then
        if cmp -s "$root_copy" "$github_copy"; then
            rm -f "$root_copy"
            echo -e "  ${GREEN}OK${RESET} Removed redundant legacy root copy: copilot-instructions.md"
        else
            echo -e "  ${YELLOW}WARN${RESET} Legacy root copy differs from canonical .github/copilot-instructions.md; manual review required"
        fi
    fi
}
ensure_gitignore_block() {
    local gitignore="$TARGET_DIR/.gitignore"
    local begin="# --- kuro-rules private research ---"
    local end="# --- end kuro-rules private research ---"

    if [ ! -f "$gitignore" ]; then
        touch "$gitignore"
    fi

    if ! grep -Fq "$begin" "$gitignore"; then
        cat >> "$gitignore" <<EOF
$begin
mom_test_results.md
mom_test_script.md
decision.md
ideas.md
architecture_notes.md
concept/
research/private/
research/raw/
research/interviews/
research/contact-lists/
notes-private.md
contacts.csv
leads.csv
prospects.csv
$end
EOF
        echo -e "  ${GREEN}OK${RESET} Updated: .gitignore"
    else
        echo -e "  ${BLUE}INFO${RESET} .gitignore already has managed private block"
    fi
}

apply_project_defaults

echo -e "${BLUE}Installing shared rules into: $TARGET_DIR${RESET}"

link_file "$RULES_DIR/AGENTS.md" "$TARGET_DIR/AGENTS.md"
link_file "$RULES_DIR/AI_GUIDELINES.md" "$TARGET_DIR/AI_GUIDELINES.md"
link_file "$RULES_DIR/GAD.md" "$TARGET_DIR/GAD.md"
link_file "$RULES_DIR/.cursorrules" "$TARGET_DIR/.cursorrules"
link_file "$RULES_DIR/copilot-instructions.md" "$TARGET_DIR/.github/copilot-instructions.md"

copy_if_missing "$RULES_DIR/.pre-commit-config.yaml" "$TARGET_DIR/.pre-commit-config.yaml"

render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/decision-memo.md" "$TARGET_DIR/decision-memo.md"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/prompts/perplexity.md" "$TARGET_DIR/prompts/perplexity.md"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/prompts/grok.md" "$TARGET_DIR/prompts/grok.md"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/research/README.md" "$TARGET_DIR/research/README.md"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/research/evidence-matrix.csv" "$TARGET_DIR/research/evidence-matrix.csv"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/research/scorecard.md" "$TARGET_DIR/research/scorecard.md"
render_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/research/open-questions.md" "$TARGET_DIR/research/open-questions.md"
copy_if_missing "$RULES_DIR/PROJECT_SCAFFOLD/research/.gitignore" "$TARGET_DIR/research/.gitignore"

ensure_gitignore_block

echo -e "\n${GREEN}Success!${RESET} Rules and validation scaffold installed."
echo -e "Project prompts now live in ${YELLOW}prompts/${RESET} and staged validation lives in ${YELLOW}research/${RESET}."
