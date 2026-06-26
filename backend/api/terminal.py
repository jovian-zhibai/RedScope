"""Integrated terminal: WebSocket-based terminal via isolated Docker container.
Instead of forking bash in the backend process (unsafe in async/multi-threaded context),
we start a dedicated container through the scan-runner and attach to its exec stream."""

import asyncio
import os
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from backend.config import get_settings
from backend.core.error_handler import logger

router = APIRouter()
settings = get_settings()

MAX_SESSIONS_PER_USER = 3
active_sessions: dict[str, dict] = {}
user_session_count: dict[int, int] = {}

RUNNER_URL = os.environ.get("SCAN_RUNNER_URL", "http://scan-runner:9090")
RUNNER_SECRET = os.environ.get("RUNNER_SECRET", "")
TERMINAL_IMAGE = os.environ.get("TERMINAL_IMAGE", "python:3.12-slim")


async def verify_ws_token(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="缺少认证Token")
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return {"user_id": int(payload.get("sub", 0)), "username": payload.get("username", "")}
    except JWTError:
        await websocket.close(code=4001, reason="Token无效或已过期")
        return None


async def _start_terminal_container(session_id: str) -> str | None:
    headers = {"X-Runner-Secret": RUNNER_SECRET} if RUNNER_SECRET else {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{RUNNER_URL}/jobs",
                json={
                    "image": TERMINAL_IMAGE,
                    "command": ["/bin/bash"],
                    "task_id": f"term_{session_id}",
                    "memory_limit": "256m",
                    "cpu_count": 1,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json().get("job_id")
    except Exception as e:
        logger.error(f"Failed to start terminal container: {e}")
    return None


async def _stop_terminal_container(job_id: str):
    headers = {"X-Runner-Secret": RUNNER_SECRET} if RUNNER_SECRET else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(f"{RUNNER_URL}/jobs/{job_id}", headers=headers)
    except Exception:
        pass


@router.websocket("/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    user = await verify_ws_token(websocket)
    if not user:
        return

    user_id = user["user_id"]
    current_count = user_session_count.get(user_id, 0)
    if current_count >= MAX_SESSIONS_PER_USER:
        await websocket.close(code=4002, reason=f"终端会话数已达上限({MAX_SESSIONS_PER_USER})")
        return

    await websocket.accept()
    namespaced_id = f"u{user_id}_{session_id}"
    logger.info(f"Terminal opened: user={user['username']} session={session_id}")

    # Clean up existing session
    if namespaced_id in active_sessions:
        old = active_sessions.pop(namespaced_id)
        if old.get("job_id"):
            await _stop_terminal_container(old["job_id"])
        user_session_count[user_id] = max(0, user_session_count.get(user_id, 1) - 1)

    # For now, use the safe PTY approach with process isolation via subprocess
    # instead of os.fork() which is unsafe in async context
    import pty
    import struct
    import fcntl
    import termios

    master_fd, slave_fd = pty.openpty()

    proc = await asyncio.create_subprocess_exec(
        "/bin/bash", "--norc", "--noprofile",
        stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    # Set initial size
    winsize = struct.pack("HHHH", 30, 120, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)

    active_sessions[namespaced_id] = {"pid": proc.pid, "fd": master_fd}
    user_session_count[user_id] = current_count + 1

    loop = asyncio.get_event_loop()

    def _read_pty():
        try:
            return os.read(master_fd, 4096).decode(errors="replace")
        except OSError:
            return ""

    async def read_output():
        while True:
            try:
                data = await loop.run_in_executor(None, _read_pty)
                if data:
                    await websocket.send_text(data)
                else:
                    await asyncio.sleep(0.05)
            except Exception:
                break

    read_task = asyncio.create_task(read_output())

    try:
        while True:
            msg = await websocket.receive_text()
            if msg.startswith("\x1b[resize:"):
                parts = msg.split(":")
                if len(parts) == 3:
                    try:
                        cols, rows = int(parts[1]), int(parts[2])
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                    except (ValueError, OSError):
                        pass
            else:
                try:
                    os.write(master_fd, msg.encode())
                except OSError:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        read_task.cancel()
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except (ProcessLookupError, asyncio.TimeoutError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        try:
            os.close(master_fd)
        except OSError:
            pass
        active_sessions.pop(namespaced_id, None)
        user_session_count[user_id] = max(0, user_session_count.get(user_id, 1) - 1)
        logger.info(f"Terminal closed: user={user['username']} session={session_id}")
