#!/usr/bin/env bash
# Install skills from agents/research_harness/skills/ to .agents/skills/
# Creates symlinks so opencode can discover and load the skills.
# Idempotent: re-running converges to the same state.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_SKILLS_DIR="$(cd "$SCRIPT_DIR/../skills" && pwd)"
OPENCODE_SKILLS_DIR="$(cd "$HARNESS_SKILLS_DIR/../../../.agents/skills" 2>/dev/null && pwd || echo "")"

if [ -z "$OPENCODE_SKILLS_DIR" ]; then
    OPENCODE_SKILLS_DIR="$(cd "$HARNESS_SKILLS_DIR/../../.." && pwd)/.agents/skills"
    mkdir -p "$OPENCODE_SKILLS_DIR"
fi

echo "Source: $HARNESS_SKILLS_DIR"
echo "Target: $OPENCODE_SKILLS_DIR"

installed=0
skipped=0

for skill_dir in "$HARNESS_SKILLS_DIR"/*/; do
    skill_name="$(basename "$skill_dir")"
    skill_md="$skill_dir/SKILL.md"

    if [ ! -f "$skill_md" ]; then
        echo "SKIP: $skill_name (no SKILL.md)"
        skipped=$((skipped + 1))
        continue
    fi

    target="$OPENCODE_SKILLS_DIR/$skill_name"

    if [ -L "$target" ]; then
        current_target="$(readlink "$target")"
        if [ "$current_target" = "$skill_dir" ] || [ "$current_target" = "$(cd "$skill_dir" && pwd)" ]; then
            echo "OK:   $skill_name (symlink exists)"
            skipped=$((skipped + 1))
            continue
        else
            echo "UPDATE: $skill_name (symlink points elsewhere, fixing)"
            rm "$target"
        fi
    elif [ -d "$target" ]; then
        echo "CONFLICT: $skill_name (directory exists at target, not a symlink)"
        skipped=$((skipped + 1))
        continue
    fi

    ln -s "$skill_dir" "$target"
    echo "INSTALLED: $skill_name -> $target"
    installed=$((installed + 1))
done

echo ""
echo "Done. Installed: $installed, Skipped: $skipped"
