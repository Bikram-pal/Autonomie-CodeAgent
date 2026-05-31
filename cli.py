import argparse
import shutil
import os
from agent import graph


def _blank_state(mode: str) -> dict:
    return {
        "mode": mode, "project_dir": "sandbox", "request": "",
        "intent": "", "plan": [], "proposed_changes": {},
        "heal_instructions": "", "test_output": "", "test_passed": False,
        "retry_count": 0, "needs_human": False, "human_feedback": "",
        "aborted": False
    }


def load_scenario(scenario_name: str):
    src = os.path.join("scenarios", scenario_name)
    dest = "sandbox"

    if not os.path.exists(src):
        print(f"❌ Scenario '{scenario_name}' not found in /scenarios.")
        return

    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
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
        graph.invoke(state, config={"configurable": {"thread_id": "request"}})
    else:
        parser.print_help()


if __name__ == "__main__":
    main()