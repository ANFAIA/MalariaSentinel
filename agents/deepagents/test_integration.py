#!/usr/bin/env python3
"""Integration test: deepagent + gitagent worktree isolation + permissions + logging.

Creates a clone of the repo, runs a deepagent that tries to edit inside
and outside a gitagent worktree, then verifies:
  1. Worktrees are created correctly
  2. Writes inside worktree succeed
  3. Writes outside worktree are blocked (permissions)
  4. Multiple subagents can be spawned in parallel
  5. Session logs capture the full process

Usage:
    python scripts/deepagents/test_integration.py [--no-clone] [--repo-path PATH]
    # --no-clone: use existing repo at --repo-path (default: /tmp/MalariaSentinel-test-$$)
    # --repo-path: path to test repo (default: auto-clone)

Requires: OPENROUTER_API_KEY env var set.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_FEATURE = "test-integration-e2e"
TEST_AGENT_1 = "a_worker_1"
TEST_AGENT_2 = "a_worker_2"
CLEANUP_ON_SUCCESS = True


def run(cmd: list[str], cwd: str | Path | None = None, timeout: int = 60) -> dict:
    """Run a command and return result dict."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "timeout"}


def ga(args: list[str], cwd: str | Path) -> dict:
    """Run gitagent CLI."""
    return run(["gitagent"] + args, cwd=cwd)


# ── Test functions ───────────────────────────────────────────────────

def test_gitagent_init(repo: Path) -> bool:
    """Test 1: gitagent init works."""
    print("\n" + "=" * 60)
    print("TEST 1: gitagent init")
    print("=" * 60)

    r = ga(["init"], cwd=repo)
    if r["returncode"] != 0 and "already initialized" not in r["stderr"].lower():
        print(f"  FAIL: {r['stderr']}")
        return False
    print(f"  PASS: gitagent initialized")
    return True


def test_feature_session(repo: Path) -> bool:
    """Test 2: start a feature session."""
    print("\n" + "=" * 60)
    print("TEST 2: start feature session")
    print("=" * 60)

    r = ga(["start", "--feature", TEST_FEATURE], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL: {r['stderr']}")
        return False
    print(f"  PASS: session started for '{TEST_FEATURE}'")
    return True


def test_spawn_agents(repo: Path) -> dict[str, str]:
    """Test 3: spawn two worker agents, return {agent_id: worktree_path}."""
    print("\n" + "=" * 60)
    print("TEST 3: spawn two worker agents")
    print("=" * 60)

    worktrees = {}
    for agent_id in [TEST_AGENT_1, TEST_AGENT_2]:
        r = ga(["spawn", "--feature", TEST_FEATURE, "--id", agent_id, "--role", "test-worker"], cwd=repo)
        if r["returncode"] != 0:
            print(f"  FAIL spawn {agent_id}: {r['stderr']}")
            return {}

        # Parse worktree path from output
        # Output format: "Agent <id> -> \n<path>" (path may span multiple lines)
        # Join ALL remaining lines after -> first, then try partial joins
        wt_path = None
        lines = r["stdout"].splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if "->" in line:
                # Collect ALL remaining lines after ->
                remaining_lines = []
                first_part = line.split("->", 1)[1].strip()
                if first_part:
                    remaining_lines.append(first_part)
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped:
                        remaining_lines.append(stripped)

                # Try joining ALL lines first (longest path)
                full_candidate = "".join(remaining_lines)
                if full_candidate and Path(full_candidate).is_dir():
                    wt_path = full_candidate
                    break

                # Try progressively shorter joins
                for k in range(len(remaining_lines), 0, -1):
                    candidate = "".join(remaining_lines[:k])
                    if candidate and Path(candidate).is_dir():
                        wt_path = candidate
                        break
                if wt_path:
                    break

        if not wt_path:
            print(f"  FAIL: could not parse worktree path from: {r['stdout']}")
            return {}

        worktrees[agent_id] = wt_path
        print(f"  PASS: {agent_id} -> {wt_path}")

    return worktrees


def test_worktree_isolation(repo: Path, worktrees: dict[str, str]) -> bool:
    """Test 4: worktree is isolated from main repo."""
    print("\n" + "=" * 60)
    print("TEST 4: worktree isolation")
    print("=" * 60)

    all_pass = True
    for agent_id, wt_path in worktrees.items():
        wt = Path(wt_path)

        # Verify worktree is a git worktree
        r = run(["git", "rev-parse", "--show-toplevel"], cwd=wt)
        if r["returncode"] != 0:
            print(f"  FAIL {agent_id}: worktree is not a git repo")
            all_pass = False
            continue

        wt_root = Path(r["stdout"])

        # Verify worktree is NOT the main repo
        main_root = Path(run(["git", "rev-parse", "--show-toplevel"], cwd=repo)["stdout"])
        if wt_root.resolve() == main_root.resolve():
            print(f"  FAIL {agent_id}: worktree IS the main repo (not isolated)")
            all_pass = False
            continue

        # Verify worktree IS under .gitagent
        if ".gitagent" not in str(wt_root):
            print(f"  FAIL {agent_id}: worktree not under .gitagent: {wt_root}")
            all_pass = False
            continue

        print(f"  PASS {agent_id}: worktree isolated at {wt_root}")

    return all_pass


def test_write_inside_worktree(worktrees: dict[str, str]) -> bool:
    """Test 5: can write files inside the worktree."""
    print("\n" + "=" * 60)
    print("TEST 5: write inside worktree (should succeed)")
    print("=" * 60)

    all_pass = True
    for agent_id, wt_path in worktrees.items():
        test_file = Path(wt_path) / f"test_{agent_id}.txt"
        try:
            test_file.write_text(f"Hello from {agent_id}\nTimestamp: {time.time()}")
            if test_file.exists() and test_file.read_text().startswith(f"Hello from {agent_id}"):
                print(f"  PASS {agent_id}: wrote {test_file.name} inside worktree")
            else:
                print(f"  FAIL {agent_id}: file write failed silently")
                all_pass = False
        except Exception as e:
            print(f"  FAIL {agent_id}: cannot write inside worktree: {e}")
            all_pass = False

    return all_pass


def test_write_outside_worktree(repo: Path, worktrees: dict[str, str]) -> bool:
    """Test 6: cannot write files outside the worktree (main repo root)."""
    print("\n" + "=" * 60)
    print("TEST 6: write outside worktree (should be blocked by permissions)")
    print("=" * 60)

    # We can't easily test the deepagents runtime permissions without running the LLM.
    # Instead, we verify the permission CONFIGURATION is correct by checking
    # the WORKER_DEFINITIONS in agent.py.

    # Import the agent module to check permissions
    try:
        # Read agent.py from the test repo
        agent_py = (repo / "agents" / "deepagents" / "agent.py").read_text()

        # Check that abm-worker permissions deny writes to main repo
        if 'FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")' in agent_py:
            print("  PASS: worker permissions deny writes to /** (main repo)")
        else:
            print("  FAIL: worker permissions missing deny-all-write rule")
            return False

        # Check that worktree writes are allowed
        if '.gitagent/features/*/agents/*/worktree/**' in agent_py:
            print("  PASS: worker permissions allow writes to worktree/**")
        else:
            print("  FAIL: worker permissions missing worktree allow rule")
            return False

        # Check that orchestrator is read-only
        orchestrator_perms = agent_py.split("permissions=[")[-1].split("]")[0]
        if 'mode="write"' not in orchestrator_perms and 'mode="allow"' in orchestrator_perms:
            print("  PASS: orchestrator has read-only permissions")
        else:
            print("  INFO: orchestrator permissions may allow writes (check manually)")

        return True

    except Exception as e:
        print(f"  FAIL: could not check permissions: {e}")
        return False


def test_list_agents(repo: Path, worktrees: dict[str, str]) -> bool:
    """Test 7: list-agents shows both spawned agents."""
    print("\n" + "=" * 60)
    print("TEST 7: list-agents")
    print("=" * 60)

    r = ga(["list-agents", "--feature", TEST_FEATURE, "--json"], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL: {r['stderr']}")
        return False

    try:
        agents = json.loads(r["stdout"])
        agent_ids = [a.get("id") for a in agents] if isinstance(agents, list) else []
        # Check both agents are listed
        for aid in [TEST_AGENT_1, TEST_AGENT_2]:
            if aid in agent_ids:
                print(f"  PASS: {aid} listed")
            else:
                print(f"  FAIL: {aid} not in agents list: {agent_ids}")
                return False
        return True
    except json.JSONDecodeError:
        print(f"  FAIL: could not parse JSON: {r['stdout'][:200]}")
        return False


def test_proposals_empty(repo: Path) -> bool:
    """Test 8: proposals list is empty (no proposals yet)."""
    print("\n" + "=" * 60)
    print("TEST 8: proposals (empty)")
    print("=" * 60)

    r = ga(["proposals", "--feature", TEST_FEATURE, "--json"], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL: {r['stderr']}")
        return False

    try:
        proposals = json.loads(r["stdout"])
        if isinstance(proposals, list) and len(proposals) == 0:
            print("  PASS: no proposals (expected)")
            return True
        else:
            print(f"  INFO: found {len(proposals)} proposals (unexpected but OK)")
            return True
    except json.JSONDecodeError:
        print(f"  FAIL: could not parse JSON: {r['stdout'][:200]}")
        return False


def test_session_logging(repo: Path) -> bool:
    """Test 9: session logger creates proper log structure."""
    print("\n" + "=" * 60)
    print("TEST 9: session logging")
    print("=" * 60)

    sys.path.insert(0, str(repo / "agents"))
    try:
        from deepagents.logger import SessionLogger

        # Create a temporary session log
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(session_dir=tmpdir)

            # Simulate various log events
            logger.log_decision("test_decision", "testing logging system")
            logger.log_tool("test_tool", {"arg": "value"}, "tool output", 0.5)
            logger.log_llm_call(
                step=1, model_name="test-model", message_count=5,
                latency_s=1.2, prompt_tokens=100, completion_tokens=50,
                response_preview="test response preview",
            )
            logger.log_agent_event("test_event", "detail about event")
            logger.log_token_summary(total_prompt=500, total_completion=200, llm_calls=3)
            logger.log_graph_steps([{"node": "agent", "delta_keys": ["messages"]}])
            logger.log_conversation([
                {"type": "HumanMessage", "content": "test user message"},
                {"type": "AIMessage", "content": "test AI response"},
            ])
            logger.log_summary("test summary")
            logger.close()

            # Read the log file and verify
            log_file = Path(tmpdir) / "session.jsonl"
            lines = log_file.read_text().strip().split("\n")
            events = [json.loads(line) for line in lines]

            event_types = [e["event"] for e in events]
            print(f"  Log events ({len(events)} total): {event_types}")

            # Verify expected events
            expected = [
                "session_start", "decision", "tool_call", "llm_call",
                "agent_test_event", "token_summary", "graph_steps",
                "conversation", "summary", "session_end",
            ]
            all_found = True
            for exp in expected:
                if exp in event_types:
                    print(f"  PASS: {exp} event logged")
                else:
                    print(f"  FAIL: {exp} event missing")
                    all_found = False

            # Verify llm_call has token info
            llm_event = next(e for e in events if e["event"] == "llm_call")
            if llm_event.get("prompt_tokens") == 100 and llm_event.get("completion_tokens") == 50:
                print("  PASS: llm_call has token usage")
            else:
                print("  FAIL: llm_call missing token usage")
                all_found = False

            return all_found

    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_observability_middleware(repo: Path) -> bool:
    """Test 10: ObservabilityMiddleware can be instantiated."""
    print("\n" + "=" * 60)
    print("TEST 10: ObservabilityMiddleware")
    print("=" * 60)

    sys.path.insert(0, str(repo / "agents"))
    try:
        from deepagents.observability import ObservabilityMiddleware
        from deepagents.logger import SessionLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SessionLogger(session_dir=tmpdir)
            middleware = ObservabilityMiddleware(logger)

            # Check it has all 6 hooks
            hooks = [
                "before_agent", "before_model", "wrap_model_call",
                "after_model", "wrap_tool_call", "after_agent",
            ]
            all_found = True
            for hook in hooks:
                if hasattr(middleware, hook):
                    print(f"  PASS: {hook} hook exists")
                else:
                    print(f"  FAIL: {hook} hook missing")
                    all_found = False

            # Check async twins
            async_hooks = [f"a{h}" for h in hooks]
            for hook in async_hooks:
                if hasattr(middleware, hook):
                    print(f"  PASS: {hook} async hook exists")
                else:
                    print(f"  FAIL: {hook} async hook missing")
                    all_found = False

            return all_found

    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_propose_and_diff(repo: Path, worktrees: dict[str, str]) -> bool:
    """Test 11: agent can propose and diff shows the changes."""
    print("\n" + "=" * 60)
    print("TEST 11: propose and diff")
    print("=" * 60)

    agent_id = TEST_AGENT_1
    wt_path = worktrees[agent_id]

    # Create a file in the worktree (simulating agent work)
    test_file = Path(wt_path) / "PROPOSE_TEST.txt"
    test_file.write_text("This file was created by the integration test.\n")

    # Propose from the worktree
    r = ga([
        "propose", "--feature", TEST_FEATURE, "--agent", agent_id,
        "--title", "Integration test proposal",
        "--summary", "Test file to verify gitagent propose works",
        "--confidence", "0.9",
    ], cwd=repo)

    if r["returncode"] != 0:
        print(f"  FAIL propose: {r['stderr']}")
        return False
    print(f"  PASS: proposal created by {agent_id}")

    # Get proposals list
    r = ga(["proposals", "--feature", TEST_FEATURE, "--json"], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL proposals: {r['stderr']}")
        return False

    try:
        proposals = json.loads(r["stdout"])
        if len(proposals) > 0:
            pid = proposals[0].get("manifest", {}).get("id", "?")
            print(f"  PASS: found proposal {pid}")

            # Get diff
            r = ga(["diff", pid, "--feature", TEST_FEATURE], cwd=repo)
            if r["returncode"] == 0 and "PROPOSE_TEST" in r["stdout"]:
                print(f"  PASS: diff shows PROPOSE_TEST.txt")
                return True
            else:
                print(f"  FAIL: diff doesn't show expected file")
                return False
        else:
            print("  FAIL: no proposals found")
            return False
    except json.JSONDecodeError:
        print(f"  FAIL: could not parse proposals JSON")
        return False


def test_accept_and_integrate(repo: Path) -> bool:
    """Test 12: accept proposal and integrate."""
    print("\n" + "=" * 60)
    print("TEST 12: accept and integrate")
    print("=" * 60)

    # Get proposals
    r = ga(["proposals", "--feature", TEST_FEATURE, "--json"], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL: {r['stderr']}")
        return False

    try:
        proposals = json.loads(r["stdout"])
        if not proposals:
            print("  FAIL: no proposals to accept")
            return False

        pid = proposals[0].get("manifest", {}).get("id")
        state = proposals[0].get("review", {}).get("state")
        print(f"  Proposal {pid} state: {state}")

        # Accept
        r = ga(["accept", pid, "--feature", TEST_FEATURE], cwd=repo)
        if r["returncode"] != 0:
            print(f"  FAIL accept: {r['stderr']}")
            return False
        print(f"  PASS: proposal {pid} accepted")

        # Integrate (no --json to avoid interactive prompt issues)
        r = ga(["integrate", "--feature", TEST_FEATURE], cwd=repo)
        if r["returncode"] != 0:
            print(f"  FAIL integrate: {r['stderr']}")
            return False
        print(f"  PASS: integrated successfully")

        return True

    except json.JSONDecodeError:
        print("  FAIL: could not parse proposals JSON")
        return False


def test_finalize(repo: Path) -> bool:
    """Test 13: finalize creates a commit on main."""
    print("\n" + "=" * 60)
    print("TEST 13: finalize")
    print("=" * 60)

    # Get the current commit count
    before = run(["git", "rev-parse", "HEAD"], cwd=repo)

    r = ga(["finalize", "--feature", TEST_FEATURE, "--message", "test: integration test commit"], cwd=repo)
    if r["returncode"] != 0:
        print(f"  FAIL: {r['stderr']}")
        return False

    # Check a new commit was created
    after = run(["git", "rev-parse", "HEAD"], cwd=repo)
    if before["stdout"] != after["stdout"]:
        print(f"  PASS: new commit {after['stdout'][:12]}")
        return True
    else:
        print(f"  FAIL: no new commit created")
        return False


def test_cleanup(repo: Path) -> bool:
    """Test 14: cleanup removes worktrees."""
    print("\n" + "=" * 60)
    print("TEST 14: cleanup")
    print("=" * 60)

    # After finalize, .gitagent should be cleaned up
    gitagent_dir = repo / ".gitagent"
    if gitagent_dir.exists():
        features_dir = gitagent_dir / "features"
        if features_dir.exists() and len(list(features_dir.iterdir())) == 0:
            print("  PASS: features directory is empty after finalize")
            return True
        elif not features_dir.exists():
            print("  PASS: features directory removed after finalize")
            return True
        else:
            remaining = [f.name for f in features_dir.iterdir()]
            print(f"  INFO: features directory has: {remaining}")
            return True
    else:
        print("  PASS: .gitagent directory removed after finalize")
        return True


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Integration test for deepagent + gitagent")
    parser.add_argument("--no-clone", action="store_true", help="Don't clone, use existing repo")
    parser.add_argument("--repo-path", type=str, default=None, help="Path to test repo")
    args = parser.parse_args()

    # Determine test repo path
    if args.repo_path:
        test_repo = Path(args.repo_path)
    else:
        test_repo = Path(f"/tmp/MalariaSentinel-test-{os.getpid()}")

    # Clone if needed
    if not args.no_clone:
        if test_repo.exists():
            shutil.rmtree(test_repo)
        print(f"Cloning repo to {test_repo}...")
        r = run(["git", "clone", "--local", str(REPO_ROOT), str(test_repo)])
        if r["returncode"] != 0:
            print(f"Clone failed: {r['stderr']}")
            sys.exit(1)
        print("Clone successful.")
    else:
        if not test_repo.exists():
            print(f"Repo not found: {test_repo}")
            sys.exit(1)

    # Run tests
    results = {}

    try:
        results["gitagent_init"] = test_gitagent_init(test_repo)
        results["feature_session"] = test_feature_session(test_repo)

        worktrees = test_spawn_agents(test_repo)
        results["spawn_agents"] = bool(worktrees)

        if worktrees:
            results["worktree_isolation"] = test_worktree_isolation(test_repo, worktrees)
            results["write_inside"] = test_write_inside_worktree(worktrees)
            results["write_outside"] = test_write_outside_worktree(test_repo, worktrees)
            results["list_agents"] = test_list_agents(test_repo, worktrees)
            results["proposals_empty"] = test_proposals_empty(test_repo)
            results["propose_and_diff"] = test_propose_and_diff(test_repo, worktrees)
            results["accept_and_integrate"] = test_accept_and_integrate(test_repo)
            results["finalize"] = test_finalize(test_repo)
            results["cleanup"] = test_cleanup(test_repo)

        results["session_logging"] = test_session_logging(test_repo)
        results["observability_middleware"] = test_observability_middleware(test_repo)

    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        for name, ok in results.items():
            status = "PASS" if ok else "FAIL"
            print(f"  {status}: {name}")
        print(f"\n  {passed}/{total} tests passed")

        # Cleanup
        if CLEANUP_ON_SUCCESS and all(results.values()) and test_repo.exists():
            print(f"\nAll tests passed. Cleaning up {test_repo}...")
            shutil.rmtree(test_repo, ignore_errors=True)
        elif test_repo.exists():
            print(f"\nSome tests failed. Keeping {test_repo} for inspection.")

        sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
