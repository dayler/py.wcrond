import argparse
import sys
from .client import IPCClient
from .formatters import print_table, colorize, format_duration, format_datetime
import json

def handle_response(response, callback):
    if response.get("status") == "error":
        print(f"Error: {response.get('message', 'Unknown error')}")
        sys.exit(1)
    callback(response.get("data"))

def format_status(data):
    print(f"Uptime: {format_duration(data.get('uptime'))}")
    print(f"Jobs: {data.get('jobs', 0)}")
    print(f"Threads: {data.get('threads', 0)}")
    print(f"Retry Queue Size: {data.get('retry_queue_size', 0)}")

def cmd_status(args, client):
    resp = client.send_request({"cmd": "status"})
    handle_response(resp, format_status)

def cmd_list(args, client):
    resp = client.send_request({"cmd": "list"})
    def format_list(data):
        headers = ["Job", "Schedule", "Enabled", "Last Run"]
        rows = [[job.get("id", ""), job.get("schedule", ""), str(job.get("enabled", True)), format_datetime(job.get("last_run", "Never"))] for job in data]
        print_table(headers, rows)
    handle_response(resp, format_list)

def cmd_history(args, client):
    req = {"cmd": "history"}
    if args.job: req["job"] = args.job
    if args.last: req["limit"] = args.last
    if args.since: req["since"] = args.since
    resp = client.send_request(req)
    def format_hist(data):
        headers = ["Job", "Started", "Ended", "Duration", "Status", "Attempt", "Trigger"]
        rows = []
        for d in data:
            status = colorize(d.get('status', ''), d.get('status', ''))
            rows.append([
                d.get('job', ''),
                format_datetime(d.get('start_time', '')),
                format_datetime(d.get('end_time', '')),
                format_duration(d.get('duration_s', 0)),
                status,
                d.get('attempt', ''),
                d.get('trigger', '')
            ])
        print_table(headers, rows)
    handle_response(resp, format_hist)

def cmd_retries(args, client):
    resp = client.send_request({"cmd": "retries"})
    def format_retries(data):
        headers = ["Job", "Attempt", "Next Retry At", "Reason"]
        rows = [[d.get('job', ''), d.get('attempt', ''), format_datetime(d.get('next_retry_at', '')), d.get('reason', '')] for d in data]
        print_table(headers, rows)
    handle_response(resp, format_retries)

def cmd_run(args, client):
    resp = client.send_request({"cmd": "run", "job": args.job_id})
    handle_response(resp, lambda d: print(f"Job '{args.job_id}' submitted"))

def cmd_kill(args, client):
    resp = client.send_request({"cmd": "kill", "job": args.job_id})
    handle_response(resp, lambda d: print(f"Kill signal sent to '{args.job_id}'"))

def cmd_cancel_retry(args, client):
    resp = client.send_request({"cmd": "cancel-retry", "job": args.job_id})
    handle_response(resp, lambda d: print(f"Retries cancelled for '{args.job_id}'"))

def cmd_cancel_all_retries(args, client):
    resp = client.send_request({"cmd": "cancel-all-retries"})
    def cb(data):
        if not data:
            print("No pending retries to cancel.")
        else:
            print_table(["Job", "Status"], [[d.get("job", ""), d.get("status", "")] for d in data])
    handle_response(resp, cb)

def cmd_disable(args, client):
    resp = client.send_request({"cmd": "disable", "job": args.job_id})
    handle_response(resp, lambda d: print(f"Job '{args.job_id}' disabled"))

def cmd_enable(args, client):
    resp = client.send_request({"cmd": "enable", "job": args.job_id})
    handle_response(resp, lambda d: print(f"Job '{args.job_id}' enabled"))

def cmd_zombies(args, client):
    resp = client.send_request({"cmd": "zombies"})
    def cb(data):
        if not data:
            print("No zombies detected.")
        else:
            print_table(["Job", "PID", "Since"], [[d.get('job',''), d.get('pid',''), format_datetime(d.get('since',''))] for d in data])
    handle_response(resp, cb)

def cmd_reload(args, client):
    resp = client.send_request({"cmd": "reload"})
    handle_response(resp, lambda d: print("Configuration reloaded"))

def cmd_logs(args, client):
    req = {"cmd": "logs"}
    if args.job: req["job"] = args.job
    if args.tail: req["tail"] = args.tail
    resp = client.send_request(req)
    def cb(data):
        for line in data:
            print(line)
    handle_response(resp, cb)

def cmd_validate(args, client):
    resp = client.send_request({"cmd": "validate"})
    def cb(d):
        print("Configuration is valid")
        if isinstance(d, dict) and d.get("warnings"):
            for w in d["warnings"]:
                print(formatters.colorize(w, "TIMEOUT"))
    handle_response(resp, cb)

def cmd_next(args, client):
    req = {"cmd": "next"}
    if args.job: req["job"] = args.job
    resp = client.send_request(req)
    def cb(data):
        print_table(["Job", "Next Run At"], [[d.get("job",""), format_datetime(d.get("next_run",""))] for d in data])
    handle_response(resp, cb)

def cmd_stop(args, client):
    resp = client.send_request({"cmd": "stop"})
    handle_response(resp, lambda d: print("Stop signal sent to daemon"))

def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    parser = argparse.ArgumentParser(description="wcrond-ctl: Control CLI for wcrond")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds for IPC communication (default: 5)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_status = subparsers.add_parser("status", help="Daemon status")
    p_list = subparsers.add_parser("list", help="List all jobs")
    
    p_history = subparsers.add_parser("history", help="Execution history")
    p_history.add_argument("--job", help="Filter by job ID")
    p_history.add_argument("--last", type=int, help="Limit number of results")
    p_history.add_argument("--since", help="Filter by date (ISO format)")

    p_retries = subparsers.add_parser("retries", help="Pending retries")

    p_run = subparsers.add_parser("run", help="Force run a job")
    p_run.add_argument("job_id", help="Job ID")

    p_kill = subparsers.add_parser("kill", help="Kill a running job")
    p_kill.add_argument("job_id", help="Job ID")

    p_cancel = subparsers.add_parser("cancel-retry", help="Cancel pending retries")
    p_cancel.add_argument("job_id", help="Job ID")

    p_cancel_all = subparsers.add_parser("cancel-all-retries", help="Cancel all pending retries explicitly")

    p_disable = subparsers.add_parser("disable", help="Disable a job")
    p_disable.add_argument("job_id", help="Job ID")

    p_enable = subparsers.add_parser("enable", help="Enable a job")
    p_enable.add_argument("job_id", help="Job ID")

    p_zombies = subparsers.add_parser("zombies", help="List zombie tasks")
    
    p_reload = subparsers.add_parser("reload", help="Reload configuration")

    p_logs = subparsers.add_parser("logs", help="View recent logs")
    p_logs.add_argument("--job", help="Filter by job ID")
    p_logs.add_argument("--tail", type=int, help="Number of lines")

    p_validate = subparsers.add_parser("validate", help="Validate config files")

    p_next = subparsers.add_parser("next", help="Next scheduled runs")
    p_next.add_argument("--job", help="Filter by job ID")

    p_stop = subparsers.add_parser("stop", help="Stop daemon")

    args = parser.parse_args()
    client = IPCClient(timeout=args.timeout)

    commands = {
        "status": cmd_status,
        "list": cmd_list,
        "history": cmd_history,
        "retries": cmd_retries,
        "run": cmd_run,
        "kill": cmd_kill,
        "cancel-retry": cmd_cancel_retry,
        "cancel-all-retries": cmd_cancel_all_retries,
        "disable": cmd_disable,
        "enable": cmd_enable,
        "zombies": cmd_zombies,
        "reload": cmd_reload,
        "logs": cmd_logs,
        "validate": cmd_validate,
        "next": cmd_next,
        "stop": cmd_stop,
    }

    try:
        commands[args.command](args, client)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
