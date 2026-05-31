import json
import os
from typing import TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from tools import (read_file, write_file, list_py_files, get_git_diff, get_changed_files, run_pytest)

load_dotenv()

#state
class AgentState(TypedDict):
    mode: str
    project_dir: str
    changed_files: List[str]
    git_diff: str
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

#nodes
def router_node(state: AgentState) -> dict:
    if state["mode"] == "watch":
        diff = get_git_diff(state["project_dir"])
        changed = get_changed_files(state["project_dir"])
        result = run_pytest(state["project_dir"])
        return {
            "git_diff": diff,
            "changed_files": changed,
            "test_output": result["output"],
            "test_passed": result["passed"],
        }
    return {}


def analyze_diff_node(state: AgentState) -> dict:
    files_content = "\n".join([f"\n--- {f} ---\n{read_file(f)}" for f in state["changed_files"] if os.path.exists(f)])
    messages = [
        ("system", "Understand the developer's intent concisely from the diff."),
        ("user", f"Git diff:\n{state['git_diff']}\n\nFiles:\n{files_content}\nIntent?")
    ]
    response = llm.invoke(messages)
    return {"intent": response.text}


def analyze_codebase_node(state: AgentState) -> dict:
    files = list_py_files(state["project_dir"])
    summary = "\n".join([f"\n--- {f} ---\n{read_file(f)[:800]}" for f in files[:10]])
    messages = [
        ("system", "Summarize relevant codebase context for a feature request."),
        ("user", f"Codebase:\n{summary}\n\nRequest: {state['request']}\nSummary:")
    ]
    response = llm.invoke(messages)
    return {"intent": response.text}


def planner_node(state: AgentState) -> dict:
    messages = [
        ("system", "Return ONLY a numbered list of implementation steps."),
        ("user", f"Feature: {state['request']}\nContext: {state['intent']}\nPlan:")
    ]
    response = llm.invoke(messages)
    plan = [l.strip() for l in response.text.splitlines() if l.strip()]
    return {"plan": plan}


def hitl_check_node(state: AgentState) -> dict:
    plan_text = " ".join(state.get("plan", [])).lower()
    major_signals = ["new file", "create file", "add dependency", "database", "schema"]
    is_major = any(s in plan_text for s in major_signals)

    if not is_major:
        return {"needs_human": False}

    print("\n📋 Plan:")
    for i, step in enumerate(state.get("plan", []), 1):
        print(f"  {i}. {step}")

    answer = input("\n⚠️ Major change detected. Approve? [y / n / type feedback]: ").strip()
    if answer.lower() == "n":
        print("Aborted by user.")
        return {"needs_human": True, "aborted": True}

    feedback = "" if answer.lower() == "y" else answer
    return {"needs_human": True, "human_feedback": feedback}


def code_writer_node(state: AgentState) -> dict:
    files = list_py_files(state["project_dir"])
    current = "\n".join([f"\n--- {f} ---\n{read_file(f)}" for f in files])

    context = f"Intent: {state.get('intent', '')}\n"
    if state.get("plan"):
        context += "Plan:\n" + "\n".join(state["plan"]) + "\n"
    if state.get("heal_instructions"):
        context += f"Fix this error:\n{state['heal_instructions']}\n"
    if state.get("human_feedback"):
        context += f"Human feedback: {state['human_feedback']}\n"

    messages = [
        ("system",
         'Return ONLY a valid JSON object mapping file paths to new content. Example: {"app.py": "code here"}'),
        ("user", f"{context}\n\nCurrent code:\n{current}\n\nUpdate files as JSON.")
    ]

    # Force Gemini to output valid JSON natively
    json_llm = llm.bind(response_mime_type="application/json")
    response = json_llm.invoke(messages)

    try:
        proposed = json.loads(response.text)
    except Exception as e:
        print(f"JSON parse failed: {e}")
        proposed = {}

    for rel_path, content in proposed.items():
        rel_path = rel_path.removeprefix("sandbox/").removeprefix("/")
        write_file(os.path.join(state["project_dir"], rel_path), content)

    return {"proposed_changes": proposed, "heal_instructions": "", "human_feedback": ""}


def test_runner_node(state: AgentState) -> dict:
    result = run_pytest(state["project_dir"])
    return {"test_output": result["output"], "test_passed": result["passed"]}


def self_healer_node(state: AgentState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    print(f"\n[Agent] Tests failed. Attempting to heal (Try {retry_count}/{8})...")

    files = list_py_files(state["project_dir"])
    current = "\n".join([f"\n--- {f} ---\n{read_file(f)}" for f in files])

    messages = [
        ("system", "You are a debugger. Be precise: what file, what function, what exact fix?"),
        ("user", f"Test output:\n{state['test_output']}\n\nCurrent code:\n{current}\n\nFix instructions:")
    ]
    response = llm.invoke(messages)

    return {"heal_instructions": response.text, "retry_count": retry_count}


def escalator_node(state: AgentState) -> dict:
    print(f"\n❌ Could not fix after {state.get('retry_count', 0)} attempts.")
    print(f"\nLast test output:\n{state['test_output']}")
    hint = input("\n💡 Provide a hint for the agent: ").strip()
    return {"human_feedback": hint, "retry_count": 0}


#routing
def route_after_router(state: AgentState) -> str:
    if state["mode"] == "watch":
        return END if state.get("test_passed") else "analyze_diff"
    return "analyze_codebase"


def route_after_test(state: AgentState) -> str:
    if state.get("test_passed"):
        print("\n✅ All tests passed!")
        return END
    if state.get("retry_count", 0) >= 8:
        return "escalator"
    return "self_healer"


def route_after_hitl(state: AgentState) -> str:
    if state.get("aborted"):
        return END
    return "code_writer"


#graph
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("router", router_node)
    g.add_node("analyze_diff", analyze_diff_node)
    g.add_node("analyze_codebase", analyze_codebase_node)
    g.add_node("planner", planner_node)
    g.add_node("hitl_check", hitl_check_node)
    g.add_node("code_writer", code_writer_node)
    g.add_node("test_runner", test_runner_node)
    g.add_node("self_healer", self_healer_node)
    g.add_node("escalator", escalator_node)

    g.set_entry_point("router")

    g.add_conditional_edges("router", route_after_router, {
        "analyze_diff": "analyze_diff",
        "analyze_codebase": "analyze_codebase",
        END: END
    })
    g.add_edge("analyze_diff", "code_writer")
    g.add_edge("analyze_codebase", "planner")
    g.add_edge("planner", "hitl_check")
    g.add_conditional_edges("hitl_check", route_after_hitl, {
        "code_writer": "code_writer",
        END: END
    })
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