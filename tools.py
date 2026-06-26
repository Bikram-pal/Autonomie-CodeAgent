import subprocess
import json
import re
from pathlib import Path
from typing import List

#file
def read_file(path:str) -> str:
    """reads a file"""
    return Path(path).read_text(encoding="utf-8")

def write_file(path:str, content:str) -> None:
    """writes a file"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def list_project_files(dir: str) -> List[str]:
    """Lists relevant codebase files while ignoring node_modules, dist, etc."""
    extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".yml", "json", ".txt"}
    ignore_dirs = {"node_modules", "dist", "build", "__pycache__", ".venv", ".autonomie_backup"}

    files = []
    for p in Path(dir).rglob("*"):
        if p.is_file() and p.suffix in extensions:
            # Check if any part of the file's path is in our ignore list
            if not any(ignored in p.parts for ignored in ignore_dirs):
                files.append(str(p))
    return files

def _detect_ecosystem(dir: str) -> str:
    """Detects if the project is Node.js or Python."""
    if (Path(dir) / "package.json").exists():
        return "node"
    return "python"

#tests
def run_tests(dir: str) -> dict:
    """Ecosystem-aware test runner (Pytest or npm/Jest)"""
    ecosystem = _detect_ecosystem(dir)
    output = ""

    for _ in range(2):
        if ecosystem == "node":
            cmd = ["npm", "test"]
            missing_pkg_regex = r"Cannot find module '([^']+)'"
            install_cmd = ["npm", "install"]
            no_test_str = "Error: no test specified"
        else:
            cmd = ["pytest", "--tb=short", "-q"]
            missing_pkg_regex = r"ModuleNotFoundError: No module named '(\w+)'"
            install_cmd = ["pip", "install"]
            no_test_str = "collected 0 items"

        result = subprocess.run(cmd, cwd=dir, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        passed = result.returncode == 0

        # Auto-heal missing dependencies dynamically for both JS and Python
        match = re.search(missing_pkg_regex, output)
        if match:
            module = match.group(1)
            print(f"\n📦 Missing package detected. Auto-installing '{module}'...")
            subprocess.run(install_cmd + [module], cwd=dir, capture_output=True)
            continue

        # Detect missing tests
        if no_test_str in output or "no tests ran" in output.lower():
            passed = False
            output = "NO TESTS FOUND. You must write tests (pytest for Python, jest for Node) for the existing code."

        return {"passed": passed, "output": output}

    return {"passed": False, "output": output}

COVERAGE_THRESHOLD = 90


def run_tests_coverage(dir: str) -> dict:
    """Ecosystem-aware test runner with branch coverage."""
    ecosystem = _detect_ecosystem(dir)
    output = ""
    branch_coverage = 100.0  # fail-open default

    for _ in range(2):
        if ecosystem == "node":
            # Jest requires --coverage flag. It outputs to coverage/coverage-summary.json
            cmd = ["npx", "jest", "--coverage", "--coverageReporters=json-summary"]
            missing_pkg_regex = r"Cannot find module '([^']+)'"
            install_cmd = ["npm", "install"]
            no_test_str = "No tests found"
        else:
            cmd = ["pytest", "--tb=short", "-q", "--cov=.", "--cov-branch", "--cov-report=json:coverage.json"]
            missing_pkg_regex = r"ModuleNotFoundError: No module named '(\w+)'"
            install_cmd = ["pip", "install"]
            no_test_str = "collected 0 items"

        result = subprocess.run(cmd, cwd=dir, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        passed = result.returncode == 0

        match = re.search(missing_pkg_regex, output)
        if match:
            module = match.group(1)
            print(f"\n📦 Missing package detected. Auto-installing '{module}'...")
            subprocess.run(install_cmd + [module], cwd=dir, capture_output=True)
            continue

        if no_test_str in output or "no tests ran" in output.lower():
            return {
                "passed": False,
                "output": "NO TESTS FOUND. Write tests to proceed.",
                "branch_coverage": 0.0
            }

        # Parse coverage based on ecosystem
        try:
            if ecosystem == "node":
                cov_path = Path(dir) / "coverage" / "coverage-summary.json"
                if cov_path.exists():
                    cov_data = json.loads(cov_path.read_text())
                    total_branches = cov_data.get("total", {}).get("branches", {}).get("total", 0)
                    covered = cov_data.get("total", {}).get("branches", {}).get("covered", 0)
                    if total_branches > 0:
                        branch_coverage = (covered / total_branches) * 100
            else:
                cov_path = Path(dir) / "coverage.json"
                if cov_path.exists():
                    cov_data = json.loads(cov_path.read_text())
                    totals = cov_data.get("totals", {})
                    num_branches = totals.get("num_branches", 0)
                    covered_branches = totals.get("covered_branches", 0)
                    if num_branches > 0:
                        branch_coverage = (covered_branches / num_branches) * 100
        except Exception:
            pass  # Fail open on parse error

        return {
            "passed": passed,
            "output": output,
            "branch_coverage": round(branch_coverage, 1)
        }

    return {"passed": False, "output": output, "branch_coverage": 0.0}
