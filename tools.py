import subprocess
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

def list_py_files(dir:str) -> List[str]:
    """lists all python files in a directory"""
    return [str(p) for p in Path(dir).rglob("*.py") if "__pycache__" not in str(p)]

#tests
def run_pytest(dir: str) -> dict:
    # We loop twice to allow for an auto-install retry if a package is missing
    for _ in range(2):
        result = subprocess.run(["pytest", "--tb=short", "-q"], cwd=dir, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        passed = result.returncode == 0

        # Auto-install missing packages dynamically!
        match = re.search(r"ModuleNotFoundError: No module named '(\w+)'", output)
        if match:
            module = match.group(1)
            print(f"\n📦 Missing package detected. Auto-installing '{module}' via pip...")
            subprocess.run(["pip", "install", module], capture_output=True)
            continue  # Rerun pytest after install

        # Handle the edge case where no test files exist
        if "collected 0 items" in output or "no tests ran" in output:
            passed = False
            output = "NO TESTS FOUND. You must write a pytest file (e.g. test_app.py) that tests the existing code."

        return {"passed": passed, "output": output}

    return {"passed": False, "output": output}