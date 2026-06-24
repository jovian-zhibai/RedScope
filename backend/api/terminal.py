"""Integrated terminal: WebSocket-based terminal with JWT authentication."""

import asyncio
import pty
import os
import struct
import fcntl
import termios
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from backend.config import get_settings
from backend.core.error_handler import logger

router = APIRouter()
settings = get_settings()

MAX_SESSIONS_PER_USER = 3
sessions: dict[str, "TerminalSession"] = {}
user_session_count: dict[int, int] = {}


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


class TerminalSession:
    def __init__(self, user_id: int):
        self.fd = None
        self.pid = None
        self.user_id = user_id

    def start(self, cols: int = 120, rows: int = 30):
        pid, fd = pty.openpty()
        self.pid = os.fork()
        if self.pid == 0:
            os.setsid()
            os.dup2(fd, 0)
            os.dup2(fd, 1)
            os.dup2(fd, 2)
            os.execvp("/bin/bash", ["/bin/bash", "--restricted", "-l"])
        else:
            self.fd = fd
            self.resize(cols, rows)

    def resize(self, cols: int, rows: int):
        if self.fd:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    def write(self, data: str):
        if self.fd:
            os.write(self.fd, data.encode())

    def read(self, size: int = 4096) -> str:
        if self.fd:
            try:
                return os.read(self.fd, size).decode(errors="replace")
            except OSError:
                return ""
        return ""

    def stop(self):
        if self.pid:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
        if self.fd:
            try:
                os.close(self.fd)
            except OSError:
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
    logger.info(f"Terminal opened: user={user['username']} session={session_id}")

    session = TerminalSession(user_id)
    session.start()
    sessions[session_id] = session
    user_session_count[user_id] = current_count + 1

    async def read_output():
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, session.read)
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
                    session.resize(int(parts[1]), int(parts[2]))
            else:
                session.write(msg)
    except WebSocketDisconnect:
        pass
    finally:
        read_task.cancel()
        session.stop()
        sessions.pop(session_id, None)
        user_session_count[user_id] = max(0, user_session_count.get(user_id, 1) - 1)
        logger.info(f"Terminal closed: user={user['username']} session={session_id}")
