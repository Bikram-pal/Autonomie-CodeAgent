# Autonomie: An Autonomous Self-Healing TDD Coding Agent

Autonomie is an experimental, lightweight AI coding agent designed to demonstrate how strict state-machines can automate software development using **Test-Driven Development (TDD)** and **Self-Healing Loops**.

Rather than relying on overly complex and unpredictable autonomous multi-agent frameworks, Autonomie uses a deterministic state-machine built on **LangGraph** and powered by **Gemini 3.1 Flash Lite** (via LangChain). It is designed to be highly reliable, running completely inside a local Python environment without Git or filesystem watch overhead.

---

## 🔑 Key Architectural Features

**Full-Stack & Multi-Language Support**
Autonomie natively supports Python (via `pytest`) and JavaScript/TypeScript (via `jest`). It auto-detects your ecosystem via `package.json` or `requirements.txt` and dynamically auto-installs missing dependencies (`pip install` / `npm install`) during test execution.

**The Test Coverage Gatekeeper (`test_verifier_node`)**
The agent strictly enforces TDD. It will refuse to write or edit implementation code until it verifies a comprehensive test suite exists. **Furthermore, it measures branch coverage.** If test coverage is below 90%, it will autonomously write edge-case tests (nulls, division-by-zero, negative numbers) to bulletproof the code before it attempts any refactoring.

**Self-Healing Execution Loop**
When a test fails, the agent captures the traceback, analyzes the failure, drafts a targeted code fix, and re-runs the tests. It repeats this cycle up to 3 times before escalating to a human.

**Context-Aware Requests (`--context`)**
Pass a spec sheet, design doc, or ticket directly to the agent. It integrates the external file directly into its planning phase, ensuring new features adhere precisely to your architecture rules.

---

## 📁 Project Structure

```
Autonomie-CodeAgent/
├── scenarios/
│   ├── 01_math_app/         # Python buggy baseline
│   └── 02_node_app/         # Node.js buggy baseline
├── sandbox/                 # Live playground (ignored by git, loaded dynamically)
├── agent.py                 # LangGraph state machine & Gemini nodes
├── tools.py                 # File I/O, Pytest/Jest execution & auto-pip/npm installer
├── cli.py                   # Terminal entry point (load, check, request)
└── requirements.txt         # Package dependencies
```

---

## 🚀 Getting Started

Follow these steps to clone, set up, and run the agent locally.

### 1. Clone the Repository

```bash
git clone https://github.com/Macmill-340/Autonomie-CodeAgent.git
cd Autonomie-CodeAgent
```

### 2. Set Up a Virtual Environment & Install Dependencies

```bash
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Mac/Linux)
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Your API Key

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Create a `.env` file in the root directory and add it:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 💻 How to Use

Autonomie operates using a **Scenario-based Workflow**. Load a broken scenario, run the tests, and let the agent fix it.

### Step 1: Load a Scenario

```bash
python cli.py load 02_node_app
```

### Step 2: Run the TDD Check

```bash
python cli.py check
```

What happens under the hood:

1. **Verification** — Scans the sandbox and measures test coverage via `jest`.
2. **Edge-Case Generation** — Realizes branch coverage is low, autonomously writes edge-case tests to achieve >90% coverage.
3. **Execution & Healing** — Runs tests, catches bugs, reads tracebacks, and rewrites code until ✅ All tests passed!

### Step 3: Request a New Feature (With Context)

Ask the agent to build something new, guided by a spec file:

```bash
python cli.py request "build a user login system" --context my_spec.md
```

The agent will plan the steps, pause for your **Human-In-The-Loop** approval, and execute the changes.

---

## 🛠️ How It Works (The State Machine)

Autonomie relies on a robust cyclic graph designed in LangGraph. Instead of relying on raw prompts to preserve state, LangGraph manages the agent's memory thread natively:

```
[User Trigger]
     │
     ▼
 [router]
     │
     ▼
[test_verifier] ──(Ensures test files exist & coverage ≥ 90%)
     │
     ├──────────────────────────────────┐
     ▼ (check mode)                     ▼ (request mode)
[test_runner]                    [analyze_codebase]
     │                                  │
     ├─────────────┐                    ▼
     ▼ (pass)      ▼ (fail)         [planner]
    [END]     [self_healer]             │
                   │                    ▼
                   ▼              [hitl_check] ──(Ask human if major change)
             [code_writer]             │
                   │                   ▼
                   └──────────────► [code_writer]
                                        │
                                        ▼
                                  [test_runner]
```

**Human-in-the-Loop (HITL)**
If a plan contains keywords like `new file`, `database`, or `dependency`, the agent pauses in the CLI and waits for you to type `y` to approve, `n` to abort, or provide custom feedback to modify the plan.

**Escalation Policy**
If the self-healing loop fails to resolve an issue after 3 attempts, it triggers the `escalator` node, presenting the raw traceback to the developer and asking for a manual text hint to get the agent back on track.

---

## 🤝 Contributing & Extending

This project is built to be easily extensible. To test more complex behaviors, add custom scenarios:

1. Create a new folder under `scenarios/` (e.g., `scenarios/03_fastapi_endpoints/`).
2. Add your buggy implementation files there.
3. Run `python cli.py load 03_fastapi_endpoints` and watch the agent adapt.

Pull requests are welcome! Feel free to open an issue or submit a PR at [github.com/Macmill-340/Autonomie-CodeAgent](https://github.com/Macmill-340/Autonomie-CodeAgent).