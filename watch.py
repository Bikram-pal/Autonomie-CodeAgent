import threading
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from agent import graph

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "sandbox")

def _blank_state(mode: str) -> dict:
    return {
        "mode": mode, "project_dir": PROJECT_DIR,
        "changed_files": [], "git_diff": "", "request": "",
        "intent": "", "plan": [], "proposed_changes": {},
        "heal_instructions": "", "test_output": "", "test_passed": False,
        "retry_count": 0, "needs_human": False, "human_feedback": "",
        "aborted": False
    }

def run_watch_mode():
    state = _blank_state("watch")
    graph.invoke(state, config={"configurable": {"thread_id": "watch"}})

def run_request_mode(request: str):
    state = _blank_state("request")
    state["request"] = request
    graph.invoke(state, config={"configurable": {"thread_id": "request"}})

class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._timer = None

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py") or "__pycache__" in event.src_path:
            return
        if self._timer: self._timer.cancel()
        self._timer = threading.Timer(2.0, self._trigger)
        self._timer.start()

    def _trigger(self):
        print("\n🔍 Change detected - running agent...")
        run_watch_mode()

def watch():
    handler = ChangeHandler()
    observer = Observer()
    observer.schedule(handler, PROJECT_DIR, recursive=True)
    observer.start()

    print(f"👀 Watching {PROJECT_DIR}")
    print("Ctrl+C to stop  |  use 'python cli.py request \"...\"' in another terminal\n")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()