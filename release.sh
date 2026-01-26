#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Cortex Orchestrator Release Script ===${NC}\n"

# Stage all changes
echo -e "${YELLOW}Staging all changes...${NC}"
git add .

# Check if there are any changes to commit
if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit.${NC}"
    SKIP_COMMIT=true
else
    echo -e "${GREEN}Changes staged successfully.${NC}"
    SKIP_COMMIT=false
fi

# Get the last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.2.0")
echo -e "\n${BLUE}Last tag: ${LAST_TAG}${NC}"

# Parse version parts (assuming format: vX.Y.Z)
if [[ $LAST_TAG =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    
    # Increment patch version
    NEW_PATCH=$((PATCH + 1))
    NEW_TAG="v${MAJOR}.${MINOR}.${NEW_PATCH}"
else
    echo -e "${YELLOW}Warning: Could not parse tag format, using v0.2.1${NC}"
    NEW_TAG="v0.2.1"
fi

echo -e "${GREEN}New tag: ${NEW_TAG}${NC}\n"

# Prompt for commit message if there are changes
if [ "$SKIP_COMMIT" = false ]; then
    echo -e "${YELLOW}Enter commit message (or press Enter for default):${NC}"
    read -r COMMIT_MSG
    
    if [ -z "$COMMIT_MSG" ]; then
        COMMIT_MSG="Release ${NEW_TAG}"
    fi
    
    echo -e "\n${YELLOW}Committing changes...${NC}"
    git commit -m "$COMMIT_MSG"
    echo -e "${GREEN}Changes committed.${NC}\n"
fi

# Create the new tag
echo -e "${YELLOW}Creating tag ${NEW_TAG}...${NC}"
git tag "$NEW_TAG"
echo -e "${GREEN}Tag created successfully.${NC}\n"

# Push to remote
echo -e "${YELLOW}Pushing to remote...${NC}"
git push origin main
git push origin --tags
echo -e "${GREEN}Pushed to remote successfully.${NC}\n"

echo -e "${GREEN}=== Release ${NEW_TAG} completed! ===${NC}"
