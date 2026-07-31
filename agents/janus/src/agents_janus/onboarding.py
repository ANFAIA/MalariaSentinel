"""Onboarding orchestrator — read-mostly, YAML-menu-driven."""
from __future__ import annotations
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MENU_PATH = Path(__file__).resolve().parent / "config" / "onboarding_menu.yaml"


def load_menu() -> dict:
    """Load the onboarding menu from YAML."""
    import yaml
    if not _MENU_PATH.exists():
        return {"greeting": "Hola — no hay menú configurado.", "menu": []}
    return yaml.safe_load(_MENU_PATH.read_text())


def run_onboarding(
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
) -> str:
    """Run the interactive onboarding menu.

    Shows menu items, collects user input, and either handles locally
    or hands off to the improvement orchestrator.
    """
    menu_data = load_menu()
    greeting = menu_data.get("greeting", "Hola.")
    items = menu_data.get("menu", [])

    print("\n" + "=" * 70, file=sys.stderr)
    print(greeting, file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['label']} — {item.get('description', '')}", file=sys.stderr)

    print("\nElige una opción (número):", file=sys.stderr)

    try:
        choice = input("   > ").strip()
    except (EOFError, KeyboardInterrupt):
        return json.dumps({"status": "interrupted"})

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            selected = items[idx]
        else:
            return json.dumps({"error": f"Opción fuera de rango: {choice}", "status": "error"})
    except ValueError:
        return json.dumps({"error": f"Entrada inválida: {choice}", "status": "error"})

    # Handle no_handoff items locally
    if selected.get("no_handoff"):
        return _handle_local(selected, provider, model)

    # Collect follow-up answers
    answers = {}
    for follow_up in selected.get("follow_up", []):
        question = follow_up["question"]
        key = follow_up["key"]

        if follow_up.get("free_text"):
            print(f"\n{question}", file=sys.stderr)
            try:
                answers[key] = input("   > ").strip()
            except (EOFError, KeyboardInterrupt):
                return json.dumps({"status": "interrupted"})
        elif follow_up.get("options_from"):
            # Dynamic options — call the function
            func_name = follow_up["options_from"]
            print(f"\n{question}", file=sys.stderr)
            # For now, show placeholder
            print("  (cargando opciones...)", file=sys.stderr)
            answers[key] = input("   > ").strip()
        else:
            options = follow_up.get("options", [])
            print(f"\n{question}", file=sys.stderr)
            for j, opt in enumerate(options, 1):
                print(f"  {j}. {opt}", file=sys.stderr)
            try:
                ans = input("   > ").strip()
                try:
                    answers[key] = options[int(ans) - 1]
                except (ValueError, IndexError):
                    answers[key] = ans
            except (EOFError, KeyboardInterrupt):
                return json.dumps({"status": "interrupted"})

    # Build goal from template
    handoff = selected.get("handoff", {})
    goal_template = handoff.get("goal_template", "")
    goal = goal_template.format(**answers) if goal_template else ""

    if not goal:
        return json.dumps({"error": "No goal generated", "status": "error"})

    # Hand off to improver
    from agents_janus.tools.subagent_invoke import handoff_to_improver
    result = handoff_to_improver(goal=goal, context={"answers": answers, "menu_key": selected["key"]})
    return result


def _handle_local(item: dict, provider: str, model: str) -> str:
    """Handle items that don't hand off to the improver."""
    key = item.get("key", "")

    if key == "status":
        return _show_status()
    elif key == "list_components":
        return _list_components()
    elif key == "quit":
        return json.dumps({"status": "quit"})
    else:
        return json.dumps({"error": f"Unknown local action: {key}", "status": "error"})


def _show_status() -> str:
    """Show current status: scorecards, open plans, active investigations."""
    from agents_janus.subagents.registry import load_registry

    info = {"scorecards": [], "plans": [], "subagents": []}

    # Scorecards
    best_path = Path("runs/scorecards/best_history.json")
    if best_path.exists():
        try:
            best = json.loads(best_path.read_text())
            info["best_composite"] = best.get("composite")
            info["best_ts"] = best.get("ts")
        except (json.JSONDecodeError, OSError):
            pass

    # Plans
    plans_dir = Path("docs/plans/in-process")
    if plans_dir.exists():
        info["plans"] = [f.name for f in plans_dir.glob("*.md")]

    # Subagents
    try:
        reg = load_registry()
        info["subagents"] = list(reg.all().keys())
    except (FileNotFoundError, Exception):
        info["subagents"] = ["registry not available"]

    return json.dumps(info, indent=2)


def _list_components() -> str:
    """List all subagents with their specs."""
    try:
        from agents_janus.subagents.registry import load_registry
        reg = load_registry()
        result = []
        for name, spec in reg.all().items():
            result.append({
                "name": name,
                "description": spec.description,
                "model": f"{spec.provider}/{spec.model}",
                "plugins": list(spec.plugins),
                "edits_allow": list(spec.edits_allow),
                "mailbox_inbox": spec.mailbox_inbox,
                "spec": str(spec.spec_path) if spec.spec_path else None,
            })
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
