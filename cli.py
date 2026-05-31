import argparse
from watch import watch, run_watch_mode, run_request_mode

def main():
    parser = argparse.ArgumentParser(description="Coding Agent")
    sub    = parser.add_subparsers(dest="cmd")

    sub.add_parser("watch",  help="Watch sandbox/ for .py changes")
    sub.add_parser("check",  help="Manually trigger a test run + fix cycle")

    req = sub.add_parser("request", help="Ask the agent to add a feature")
    req.add_argument("feature", type=str, help="Feature description in quotes")

    args = parser.parse_args()

    if args.cmd == "watch":
        watch()
    elif args.cmd == "check":
        run_watch_mode()
    elif args.cmd == "request":
        run_request_mode(args.feature)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()