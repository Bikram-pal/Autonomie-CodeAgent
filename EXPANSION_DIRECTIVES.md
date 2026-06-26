# Autonomie Agent — Expansion Implementation Directives

**To the team:** The core architecture, multi-language support, and the coverage gate are complete. Please implement the remaining features in the exact order below.

---

## Step 3: The Explainability Node (Changelog Reporter)

**Goal:** Stop exiting silently on success. Tell the user exactly what files/lines were changed and why.

### 3.1 State Update (`agent.py` & `cli.py`)
- Add `change_log: List[dict]` to `AgentState`.
- Default it to `[]`.

### 3.2 Tracker (`agent.py` → `code_writer_node`)
- Before calling `write_file(path, content)`, read the existing content of the file.
- Append `{"file": path, "old": old_content, "new": content}` to `state["change_log"]`.

### 3.3 Reporter Node (`agent.py`)
- Create `report_generator_node(state)`.
- Pass `state["change_log"]` to the LLM.
- Prompt:
  > *"Summarize what files were touched, what logic changed, and why it changed. Format as clean Markdown."*
- Print the output to the terminal.

### 3.4 Graph Wiring
- Modify `route_after_test`:
  - If `test_passed` is `True` → route to `report_generator` (instead of `END`).
  - Route `report_generator` → `END`.

---

## Step 4: Test State Query

**Goal:** Create a read-only CLI command for developers to manually audit their test suites.

### 4.1 CLI Update (`cli.py`)
- Add the command: `python cli.py test-status`

### 4.2 Execution
- Do **not** invoke the LangGraph.
- Directly call `result = run_tests_coverage("sandbox")` from `tools.py`.

### 4.3 Analysis
- Take the resulting `result["output"]` and coverage metrics.
- Send them to a direct LLM call (outside the graph) with the prompt:
  > *"Analyze this coverage report. Explain in plain English which functions lack tests and what edge cases are missing."*
- Print the AI's plain-English audit report to the terminal.

---

## Step 5: Rollback & Failure Report

**Goal:** If the agent fails 3 times, revert the sandbox to the last known good state so the user's code isn't left broken.

### 5.1 Snapshotting (`tools.py`)
- Create a function `snapshot_sandbox()` that copies the `sandbox/` folder to `.autonomie_backup/last_good/`.

### 5.2 Trigger Snapshot (`agent.py`)
- Call `snapshot_sandbox()` inside `report_generator_node` — meaning it only saves **after** tests successfully pass.

### 5.3 Rollback (`agent.py` → `escalator_node`)
- If the human types `"abort"` **or** the agent hits max retries in the escalator:
  - Overwrite `sandbox/` with `.autonomie_backup/last_good/`.
  - Write a `failure_log.json` to the sandbox detailing every fix that was attempted, so the human knows what went wrong.

---

## Step 6: Audit Mode

**Goal:** Give the agent a command to generate an architectural summary and workflow diagram of the whole project.

### 6.1 CLI Update (`cli.py`)
- Add the command: `python cli.py audit`
- Route it to a new graph thread.

### 6.2 Audit Node (`agent.py`)
- Create `audit_codebase_node`.
- Call `list_project_files()` and concatenate all file contents into a single string.
- Send to the LLM with the prompt:
  > *"You are a software architect. Read this codebase. 1. Provide a high-level summary. 2. Output a Mermaid.js text diagram showing how the files and functions depend on each other."*
- Save the result to `sandbox/audit_report.md`.
