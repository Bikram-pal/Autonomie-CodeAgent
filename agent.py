import json
import os
from typing import TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from tools import (read_file, write_file, list_py_files, run_pytest)

load_dotenv()

#state
class AgentState(TypedDict):
    mode: str
    project_dir: str
    request: str
    intent: str
    plan: List[str]
    proposed_changes: dict
    heal_instructions: str
    test_output: str
    test_passed: bool
    retry_count: int
    needs_human: bool
    human_feedback: str
    aborted: bool

#model
llm = ChatGoogleGenerativeAI(
    model = "gemini-3.1-flash-lite",
    api_key = os.getenv("GEMINI_API_KEY"),
    temperature = 0.3,
    max_retries = 8,
)

json_llm = llm.bind(response_mime_type="application/json")

def _get_codebase_context(dir: str) -> str:
    files = list_py_files(dir)
    return "\n".join([f"\n--- {f} ---\n{read_file(f)}" for f in files])

#nodes
def router_node(state: AgentState) -> dict:
    #passes execution to test verifier
    return {}

def test_verifier_node(state: AgentState) -> dict:
    """The Gatekeeper: Ensures tests exist before any other action is taken."""
    current_code = _get_codebase_context(state["project_dir"])

    print("\n🔎 Verifying test coverage...")
    messages = [
        ("system",
         'You are a TDD enforcer. Review the codebase. If functions lack tests or no test files exist, output a JSON mapping of the new test files to create. Example: {"test_app.py": "import pytest..."}. If tests are fully adequate, return exactly {}'),
        ("user", f"Codebase:\n{current_code}\n\nReturn JSON:")
    ]

    response = json_llm.invoke(messages)
    try:
        proposed = json.loads(response.text)
        for rel_path, content in proposed.items():
            if content:
                print(f"   ↳ Writing missing test file: {rel_path}")
                rel_path = rel_path.removeprefix("sandbox/").removeprefix("/")
                write_file(os.path.join(state["project_dir"], rel_path), content)
    except Exception:
        pass
    return {}


def analyze_codebase_node(state: AgentState) -> dict:
    current_code = _get_codebase_context(state["project_dir"])
    messages = [
        ("system", "Summarize relevant codebase context for a feature request."),
        ("user", f"Codebase:\n{current_code}\n\nRequest: {state['request']}\nSummary:")
    ]
    return {"intent": llm.invoke(messages).text}


def planner_node(state: AgentState) -> dict:
    messages = [
        ("system",
         "Return ONLY a numbered list of implementation steps. You MUST include updating/writing tests for the new feature as a step."),
        ("user", f"Feature: {state['request']}\nContext: {state['intent']}\nPlan:")
    ]
    plan = [l.strip() for l in llm.invoke(messages).text.splitlines() if l.strip()]
    return {"plan": plan}


def hitl_check_node(state: AgentState) -> dict:
    plan_text = " ".join(state.get("plan", [])).lower()
    major_signals = ["new file", "create file", "add dependency", "database"]

    if not any(s in plan_text for s in major_signals):
        return {"needs_human": False}

    print("\n📋 Plan:")
    for i, step in enumerate(state.get("plan", []), 1):
        print(f"  {i}. {step}")

    answer = input("\n⚠️ Major change detected. Approve? [y / n / type feedback]: ").strip()
    if answer.lower() == "n":
        print("Aborted by user.")
        return {"needs_human": True, "aborted": True}

    return {"needs_human": True, "human_feedback": "" if answer.lower() == "y" else answer}


def code_writer_node(state: AgentState) -> dict:
    current_code = _get_codebase_context(state["project_dir"])

    context = f"Intent: {state.get('intent', '')}\n"
    if state.get("plan"): context += "Plan:\n" + "\n".join(state["plan"]) + "\n"
    if state.get("heal_instructions"): context += f"Fix this error:\n{state['heal_instructions']}\n"
    if state.get("human_feedback"): context += f"Human feedback: {state['human_feedback']}\n"

    messages = [
        ("system",
         'Return ONLY a valid JSON object mapping file paths to new content. Example: {"app.py": "code here"}'),
        ("user", f"{context}\n\nCurrent code:\n{current_code}\n\nUpdate files as JSON.")
    ]

    try:
        proposed = json.loads(json_llm.invoke(messages).text)
        for rel_path, content in proposed.items():
            rel_path = rel_path.removeprefix("sandbox/").removeprefix("/")
            write_file(os.path.join(state["project_dir"], rel_path), content)
    except Exception as e:
        print(f"JSON parse failed: {e}")
        proposed = {}

    return {"proposed_changes": proposed, "heal_instructions": "", "human_feedback": ""}


def test_runner_node(state: AgentState) -> dict:
    result = run_pytest(state["project_dir"])
    return {"test_output": result["output"], "test_passed": result["passed"]}


def self_healer_node(state: AgentState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    print(f"\n[Agent] Tests failed. Attempting to heal (Try {retry_count}/3)...")

    current_code = _get_codebase_context(state["project_dir"])
    messages = [
        ("system", "You are a debugger. Be precise: what file, what function, what exact fix?"),
        ("user", f"Test output:\n{state['test_output']}\n\nCurrent code:\n{current_code}\n\nFix instructions:")
    ]
    return {"heal_instructions": llm.invoke(messages).text, "retry_count": retry_count}


def escalator_node(state: AgentState) -> dict:
    print(f"\n❌ Could not fix after {state.get('retry_count', 0)} attempts.")
    print(f"\nLast test output:\n{state['test_output']}")
    hint = input("\n💡 Provide a hint for the agent: ").strip()
    return {"human_feedback": hint, "retry_count": 0}


#routing
def route_after_verifier(state: AgentState) -> str:
    return "test_runner" if state["mode"] == "check" else "analyze_codebase"

def route_after_test(state: AgentState) -> str:
    if state.get("test_passed"):
        print("\n✅ All tests passed!")
        return END
    return "escalator" if state.get("retry_count", 0) >= 3 else "self_healer"


def route_after_hitl(state: AgentState) -> str:
    return END if state.get("aborted") else "code_writer"


#graph
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("router", router_node)
    g.add_node("test_verifier", test_verifier_node)
    g.add_node("analyze_codebase", analyze_codebase_node)
    g.add_node("planner", planner_node)
    g.add_node("hitl_check", hitl_check_node)
    g.add_node("code_writer", code_writer_node)
    g.add_node("test_runner", test_runner_node)
    g.add_node("self_healer", self_healer_node)
    g.add_node("escalator", escalator_node)

    g.set_entry_point("router")

    g.add_edge("router", "test_verifier")
    g.add_conditional_edges("test_verifier", route_after_verifier, {
        "test_runner": "test_runner",
        "analyze_codebase": "analyze_codebase"
    })

    g.add_edge("analyze_codebase", "planner")
    g.add_edge("planner", "hitl_check")
    g.add_conditional_edges("hitl_check", route_after_hitl, {"code_writer": "code_writer", END: END})
    g.add_edge("code_writer", "test_runner")

    g.add_conditional_edges("test_runner", route_after_test, {
        "self_healer": "self_healer",
        "escalator": "escalator",
        END: END
    })

    g.add_edge("self_healer", "code_writer")
    g.add_edge("escalator", "code_writer")

    return g.compile(checkpointer=MemorySaver())


graph = build_graph()