# Autonomie: An Autonomous Self-Healing TDD Coding Agent

Autonomie is an experimental, lightweight AI coding agent designed to demonstrate how strict state-machines can automate software development using **Test-Driven Development (TDD)** and **Self-Healing Loops**.

Rather than relying on overly complex and unpredictable autonomous multi-agent frameworks, Autonomie uses a deterministic state-machine built on **LangGraph** and powered by **Gemini 3.1 Flash Lite** (via LangChain). It is designed to be highly reliable, running completely inside a local Python environment without Git or filesystem watch overhead.

---

## 🔑 Key Architectural Features

**TDD Gatekeeping (`test_verifier_node`)**
The agent enforces TDD. It will refuse to write or edit implementation code until it verifies a comprehensive test suite (pytest) exists. If tests are missing, it autonomously generates them first.

**Self-Healing Execution Loop**
When a test fails, the agent captures the pytest traceback, analyzes the failure, drafts a targeted code fix, and re-runs the tests. It repeats this cycle up to 3 times before escalating to a human.

**Auto-Dependency Healing**
If running tests raises a `ModuleNotFoundError`, the test runner automatically intercepts the error, runs `pip install <module>` via a subprocess, and re-runs the tests — preventing LLM confusion over environment issues.

**Deterministic Workflow Engineering**
By keeping tools at the Python graph level instead of the LLM level, the agent avoids uncontrolled loops and token waste.

---

## 📁 Project Structure

```
Autonomie-CodeAgent/
├── scenarios/               # Static, read-only testing baselines
│   └── 01_math_app/
│       └── app.py           # Contains buggy multiply/divide functions (no tests)
├── sandbox/                 # Live playground (ignored by git, loaded dynamically)
├── agent.py                 # LangGraph state machine & Gemini nodes
├── tools.py                 # File I/O, Pytest execution & auto-pip installer
├── cli.py                   # Terminal entry point (load, check, request)
├── requirements.txt         # Package dependencies
├── .env                     # API Credentials (ignored by git)
└── .gitignore               # Ignored local runtime files
```

---

## 🚀 Getting Started

Follow these steps to clone, set up, and run the agent locally.

### 1. Clone the Repository

```bash
git clone https://github.com/Macmill-340/Autonomie-CodeAgent.git
cd Autonomie-CodeAgent
```

### 2. Set Up a Virtual Environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate it (Mac/Linux)
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Your API Key

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey), then create a `.env` file in the root directory and add it:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 💻 How to Use

Autonomie operates using a **Scenario-based Workflow**. You load a broken sandbox scenario, run the tests, and let the agent fix it.

### Step 1: Load a Scenario

Load the mathematical baseline challenge (which has a bug in `multiply` and is missing division guards):

```bash
python cli.py load 01_math_app
```

This command will wipe your local `sandbox/` folder (if it exists) and copy a fresh, broken copy of the application files inside.

### Step 2: Run the TDD Check

Run the main self-healing loop:

```bash
python cli.py check
```

What happens under the hood:

1. **Test Verification** — The agent scans the sandbox and notices `test_app.py` is missing. It halts, analyzes `app.py`, and writes `test_app.py` automatically.
2. **Execution** — It runs pytest. The tests fail because `multiply(a, b)` contains a bug (`a + b` instead of `a * b`).
3. **Healing** — The agent reads the traceback, updates `multiply` to use the correct operator, and saves it.
4. **Verification** — It runs pytest again. All tests pass!

### Step 3: Request a New Feature

Ask the agent to build something new inside your clean sandbox:

```bash
python cli.py request "add a power function that takes a and b and returns a to the power of b"
```

What happens under the hood:

1. **Analyze & Plan** — The agent reads your existing codebase, summarizes it, and writes a step-by-step implementation plan.
2. **Code Generation** — It writes the `power` function into `app.py` and the corresponding unit test into `test_app.py` simultaneously.
3. **TDD Validation** — It runs the test suite to verify everything is working.

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
[test_verifier] ──(Ensures test files exist)
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

1. Create a new folder under `scenarios/` (e.g., `scenarios/02_fastapi_endpoints/`).
2. Add your buggy implementation files there.
3. Run `python cli.py load 02_fastapi_endpoints` and watch the agent adapt.

Pull requests are welcome! Feel free to open an issue or submit a PR at [github.com/Macmill-340/Autonomie-CodeAgent](https://github.com/Macmill-340/Autonomie-CodeAgent).