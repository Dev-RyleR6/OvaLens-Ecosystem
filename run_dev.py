#!/usr/bin/env python
"""
run_dev.py — OvaLens Dual-Service Development Server Runner

Launches both the FastAPI REST Backend (port 8000) and the React/Vite
Web Dashboard (port 5173) concurrently with synchronized colored logs,
health check readiness detection, port recovery, and clean signal handling.

Usage:
    python run_dev.py
    python run_dev.py --no-browser
    python run_dev.py --port-backend 8000 --port-frontend 5173
    run_dev.bat   (1-Click on Windows)
"""

import os
import sys
import time
import socket
import signal
import atexit
import argparse
import platform
import threading
import subprocess
import webbrowser
from pathlib import Path
from io import TextIOWrapper

# Ensure UTF-8 output encoding on Windows consoles
if isinstance(sys.stdout, TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if isinstance(sys.stderr, TextIOWrapper):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Enable ANSI escape sequences on Windows console
if platform.system() == "Windows":
    os.system("")

# ANSI Color Tokens (matching Foundation University theme aesthetic)
CLR_RESET   = "\033[0m"
CLR_BOLD    = "\033[1m"
CLR_MAROON  = "\033[38;2;128;0;0m"       # FU Primary Maroon #800000
CLR_GREEN   = "\033[38;2;53;122;56m"     # Agri-Green #357a38
CLR_CYAN    = "\033[38;2;6;182;212m"     # Cyan
CLR_AMBER   = "\033[38;2;217;119;6m"     # Amber / Penoy #d97706
CLR_MUTED   = "\033[38;2;148;163;184m"   # Slate 400
CLR_WHITE   = "\033[38;2;248;250;252m"   # Slate 50


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def get_pid_on_port(port: int) -> int | None:
    """Identify the PID listening on a specific port (Windows & POSIX)."""
    if platform.system() == "Windows":
        try:
            cmd = f'netstat -ano | findstr ":{port} "'
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in line and parts[1].endswith(f":{port}"):
                    return int(parts[-1])
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True, stderr=subprocess.DEVNULL)
            pids = out.strip().split()
            if pids:
                return int(pids[0])
        except Exception:
            pass
    return None


def free_port(port: int):
    """Cleanly terminate any existing process occupying a required port."""
    pid = get_pid_on_port(port)
    if pid and pid != os.getpid():
        print(f"{CLR_AMBER}[WARN] Port {port} is occupied by previous PID {pid}. Freeing port...{CLR_RESET}")
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
        time.sleep(0.8)


def stream_output(pipe, prefix: str, color: str):
    """Stream process stdout/stderr line-by-line with colored service prefix."""
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            stripped = line.rstrip("\r\n")
            if stripped:
                print(f"{color}{prefix}{CLR_RESET} {stripped}", flush=True)
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def terminate_process_tree(proc: subprocess.Popen | None):
    """Safely terminate a process and all its child processes (Windows & POSIX)."""
    if proc is None or proc.poll() is not None:
        return

    pid = proc.pid
    if platform.system() == "Windows":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    else:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass


def poll_readiness(backend_port: int, frontend_port: int, no_browser: bool, stop_event: threading.Event):
    """Poll backend and frontend ports until both are healthy, then show banner and open browser."""
    backend_ready = False
    frontend_ready = False
    max_wait = 45  # seconds
    start_time = time.time()

    while not stop_event.is_set() and (time.time() - start_time) < max_wait:
        if not backend_ready and is_port_in_use(backend_port):
            backend_ready = True
        if not frontend_ready and is_port_in_use(frontend_port):
            frontend_ready = True

        if backend_ready and frontend_ready:
            break
        time.sleep(0.5)

    if backend_ready and frontend_ready and not stop_event.is_set():
        time.sleep(0.5)  # brief settle
        banner = f"""
{CLR_BOLD}{CLR_MAROON}=============================================================================={CLR_RESET}
{CLR_BOLD}{CLR_GREEN}   [OvaLens] Hatchery Platform -- Dual Dev Servers Running{CLR_RESET}
{CLR_BOLD}{CLR_MAROON}=============================================================================={CLR_RESET}
   {CLR_BOLD}* Web Dashboard:{CLR_RESET}      {CLR_CYAN}http://localhost:{frontend_port}{CLR_RESET}
   {CLR_BOLD}* FastAPI Backend:{CLR_RESET}     {CLR_GREEN}http://127.0.0.1:{backend_port}{CLR_RESET}
   {CLR_BOLD}* Swagger API Docs:{CLR_RESET}    {CLR_AMBER}http://127.0.0.1:{backend_port}/docs{CLR_RESET}
   {CLR_BOLD}* OpenAPI Spec:{CLR_RESET}        {CLR_MUTED}http://127.0.0.1:{backend_port}/openapi.json{CLR_RESET}

   {CLR_MUTED}Press {CLR_WHITE}[Ctrl+C]{CLR_MUTED} in this terminal to shut down both servers cleanly.{CLR_RESET}
{CLR_BOLD}{CLR_MAROON}=============================================================================={CLR_RESET}
"""
        print(banner, flush=True)

        if not no_browser:
            try:
                webbrowser.open(f"http://localhost:{frontend_port}")
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Run OvaLens FastAPI Backend and React Dashboard concurrently."
    )
    parser.add_argument("--port-backend", type=int, default=8000, help="FastAPI backend port (default: 8000)")
    parser.add_argument("--port-frontend", type=int, default=5173, help="React Vite dashboard port (default: 5173)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Backend host bind (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser on startup")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn live code reloading")
    parser.add_argument("--no-kill", action="store_true", help="Do not automatically free occupied ports")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    backend_dir = repo_root / "backend"
    dashboard_dir = repo_root / "dashboard"

    print(f"\n{CLR_BOLD}{CLR_MAROON}[OvaLens]{CLR_RESET} Starting OvaLens development environment...")
    print(f"{CLR_MUTED}Repository Root: {repo_root}{CLR_RESET}")

    # 1. Pre-flight Port Checks & Auto-Free
    if not args.no_kill:
        if is_port_in_use(args.port_backend):
            free_port(args.port_backend)
        if is_port_in_use(args.port_frontend):
            free_port(args.port_frontend)

    if is_port_in_use(args.port_backend):
        print(f"{CLR_AMBER}[WARN] Port {args.port_backend} is already in use.{CLR_RESET} Use --kill or close the process.")
        sys.exit(1)
    if is_port_in_use(args.port_frontend):
        print(f"{CLR_AMBER}[WARN] Port {args.port_frontend} is already in use.{CLR_RESET} Use --kill or close the process.")
        sys.exit(1)

    # 2. Database Reachability Check
    if not is_port_in_use(5432):
        print(f"{CLR_AMBER}[WARN] PostgreSQL (port 5432) is not reachable.{CLR_RESET}")
        print(f"{CLR_MUTED}   Tip: You can start the database via:{CLR_RESET} {CLR_BOLD}docker-compose up -d postgres{CLR_RESET}\n")
    else:
        print(f"{CLR_GREEN}[OK]{CLR_RESET} PostgreSQL database detected on port 5432.")

    # 3. Frontend node_modules check
    if not (dashboard_dir / "node_modules").exists():
        print(f"{CLR_AMBER}[INFO] Installing dashboard dependencies (node_modules not found)...{CLR_RESET}")
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        subprocess.run([npm_cmd, "install"], cwd=str(dashboard_dir), check=True)

    # 4. Prepare Child Processes & Cleanup Handlers
    backend_proc = None
    frontend_proc = None
    stop_event = threading.Event()

    def cleanup():
        stop_event.set()
        if backend_proc is not None:
            terminate_process_tree(backend_proc)
        if frontend_proc is not None:
            terminate_process_tree(frontend_proc)

    atexit.register(cleanup)

    def signal_handler(sig, frame):
        print(f"\n\n{CLR_BOLD}{CLR_MAROON}[OvaLens]{CLR_RESET} Graceful shutdown signal received...")
        cleanup()
        print(f"{CLR_GREEN}[OK]{CLR_RESET} All OvaLens servers stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 5. Launch FastAPI Backend
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port_backend),
    ]
    if not args.no_reload:
        backend_cmd.append("--reload")

    print(f"{CLR_GREEN}[OK]{CLR_RESET} Launching FastAPI Backend on {args.host}:{args.port_backend}...")
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    # 6. Launch React Vite Dashboard
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    frontend_cmd = [
        npm_cmd,
        "run",
        "dev",
        "--",
        "--port", str(args.port_frontend),
        "--host"
    ]

    print(f"{CLR_GREEN}[OK]{CLR_RESET} Launching React Dashboard on port {args.port_frontend}...")
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=str(dashboard_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    # 7. Start Output Streamers
    t_backend = threading.Thread(
        target=stream_output,
        args=(backend_proc.stdout, "[Backend ]", CLR_GREEN),
        daemon=True,
        name="BackendStreamer"
    )
    t_frontend = threading.Thread(
        target=stream_output,
        args=(frontend_proc.stdout, "[Frontend]", CLR_CYAN),
        daemon=True,
        name="FrontendStreamer"
    )
    t_backend.start()
    t_frontend.start()

    # 8. Start Readiness Poller
    t_poller = threading.Thread(
        target=poll_readiness,
        args=(args.port_backend, args.port_frontend, args.no_browser, stop_event),
        daemon=True,
        name="ReadinessPoller"
    )
    t_poller.start()

    # 9. Wait for Processes
    try:
        while not stop_event.is_set():
            if backend_proc.poll() is not None:
                print(f"{CLR_AMBER}[OvaLens] Backend process exited unexpectedly with code {backend_proc.poll()}{CLR_RESET}")
                break
            if frontend_proc.poll() is not None:
                print(f"{CLR_AMBER}[OvaLens] Frontend process exited unexpectedly with code {frontend_proc.poll()}{CLR_RESET}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()

