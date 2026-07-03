import argparse
import shutil
import os
import stat
from agent import graph

def remove_readonly(func, path, _):
    """Clears the readonly bit and reattempts the removal on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def _blank_state(mode: str) -> dict:
    return {
        "mode": mode, "project_dir": "sandbox", "request": "",
        "intent": "", "plan": [], "proposed_changes": {},
        "heal_instructions": [], "test_output": "", "test_passed": False,
        "retry_count": 0, "needs_human": False, "human_feedback": "",
        "aborted": False,
        # --- New coverage defaults ---
        "branch_coverage": 0.0,
        "needs_coverage_fix": False,
        "coverage_attempts": 0,
        "context_doc": "",
        # --- Multi-fix healing defaults ---
        "pending_fixes": [],
        "current_fix_index": 0,
        "fix_retry_count": 0
    }


def load_scenario(scenario_name: str):
    src = os.path.join("scenarios", scenario_name)
    dest = "sandbox"

    if not os.path.exists(src):
        print(f"❌ Scenario '{scenario_name}' not found in /scenarios.")
        return

    # Try to delete the folder
    if os.path.exists(dest):
        shutil.rmtree(dest, onerror=remove_readonly)

    # If the folder STILL exists because PyCharm locked a hidden file (like .pytest_cache),
    # we manually delete any old Python files so we still get a clean slate.
    if os.path.exists(dest):
        for file in os.listdir(dest):
            if file.endswith(".py"):
                try:
                    os.remove(os.path.join(dest, file))
                except Exception:
                    pass

    # Forcefully copy the new files over, ignoring if the folder structure already exists
    shutil.copytree(src, dest, dirs_exist_ok=True)
    print(f"✅ Loaded scenario '{scenario_name}' into /sandbox")


def ensure_sandbox():
    if not os.path.exists("sandbox"):
        print("❌ Sandbox does not exist. Run 'python cli.py load <scenario>' first.")
        exit(1)


def main():
    parser = argparse.ArgumentParser(description="Autonomous TDD Coding Agent")
    sub = parser.add_subparsers(dest="cmd")

    load_cmd = sub.add_parser("load", help="Load a scenario into the sandbox")
    load_cmd.add_argument("name", type=str, help="Name of the scenario folder")

    sub.add_parser("check", help="Verify tests, run them, and heal bugs")

    req = sub.add_parser("request", help="Ask the agent to add a feature")
    req.add_argument("feature", type=str, help="Feature description in quotes")
    req.add_argument("--context", type=str, help="Path to a spec/design file", default=None)

    args = parser.parse_args()

    if args.cmd == "load":
        load_scenario(args.name)
    elif args.cmd == "check":
        ensure_sandbox()
        state = _blank_state("check")
        graph.invoke(state, config={"configurable": {"thread_id": "check"}})
    elif args.cmd == "request":
        ensure_sandbox()
        state = _blank_state("request")
        state["request"] = args.feature

        if args.context:
            if os.path.exists(args.context):
                state["context_doc"] = open(args.context, "r", encoding="utf-8").read()
                print(f"📄 Loaded context file: {args.context}")
            else:
                print(f"⚠️ Context file not found: {args.context}")

        graph.invoke(state, config={"configurable": {"thread_id": "request"}})
    else:
        parser.print_help()


if __name__ == "__main__":
    main()