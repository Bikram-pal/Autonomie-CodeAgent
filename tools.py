import subprocess
import os
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

#git
def ensure_git(dir:str):
    """ensures directory is a git repo"""
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=dir, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Initializing git in sandbox for diff tracking...")
        subprocess.run(["git", "init"], cwd=dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=dir, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Sandbox", "-c", "user.email=sandbox@local", "commit", "-m", "init"], cwd=dir, check=True, capture_output=True)

def get_git_diff(dir:str) -> str:
    """returns the git diff for a directory"""
    ensure_git(dir)
    subprocess.run(["git", "add", "."], cwd=dir, capture_output=True)
    result = subprocess.run(["git", "diff", "--staged"], cwd=dir, capture_output=True, text=True)
    return result.stdout or "No diff available"

def get_changed_files(dir:str) -> List[str]:
    """returns all changed files in a directory"""
    ensure_git(dir)
    subprocess.run(["git", "add", "."], cwd=dir, capture_output=True)
    result = subprocess.run(["git", "diff", "--name-only", "--staged"], cwd=dir, capture_output=True, text=True)
    return [str(Path(dir) / f.strip()) for f in result.stdout.splitlines() if f.strip().endswith(".py")]

#tests
def run_pytest(dir:str) -> dict:
    result = subprocess.run(["pytest", "--tb=short", "-q"], cwd=dir, capture_output=True, text=True, timeout=60)
    return {
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr
    }