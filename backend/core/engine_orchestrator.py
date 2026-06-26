"""Engine orchestrator: dispatches scan jobs to the isolated scan-runner service.
Backend NEVER touches Docker directly — all container operations go through
the scan-runner HTTP API, achieving full architectural isolation."""

import asyncio
import os
import shlex
import uuid
from pathlib import Path
import httpx
from backend.config import get_settings
from backend.core.plugin_manager import PluginConfig, plugin_manager
from backend.utils.sanitizer import sanitize_target
from backend.core.error_handler import logger


class EngineResult:
    def __init__(self, engine: str, success: bool, output_path: str = "", error: str = "", job_id: str = ""):
        self.engine = engine
        self.success = success
        self.output_path = output_path
        self.error = error
        self.job_id = job_id


class EngineOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.runner_url = os.environ.get("SCAN_RUNNER_URL", "http://scan-runner:9090")
        self.runner_secret = os.environ.get("RUNNER_SECRET", "")
        self._running_jobs: dict[str, str] = {}  # task_id -> job_id

    async def run_engine(
        self,
        plugin: PluginConfig,
        params: dict,
        proxy_url: str | None = None,
        task_id: str | None = None,
    ) -> EngineResult:
        task_id = task_id or str(uuid.uuid4())[:8]

        for key in ("target", "url", "domain"):
            if key in params and params[key]:
                try:
                    params[key] = sanitize_target(str(params[key]))
                except ValueError as e:
                    return EngineResult(plugin.name, False, error=f"输入校验失败: {e}")

        cmd_str = plugin_manager.build_command(plugin, params, proxy_url)

        if plugin.docker_image:
            return await self._run_via_runner(plugin, cmd_str, task_id)
        elif plugin.local_binary:
            return await self._run_local(plugin, cmd_str, task_id)
        else:
            return EngineResult(plugin.name, False, error="No docker image or local binary configured")

    async def _run_via_runner(
        self, plugin: PluginConfig, tool_cmd: str, task_id: str
    ) -> EngineResult:
        """Submit scan job to the isolated scan-runner service via HTTP."""
        cmd_args = shlex.split(tool_cmd)

        try:
            headers = {}
            if self.runner_secret:
                headers["X-Runner-Secret"] = self.runner_secret

            logger.info(f"Dispatching to scan-runner: {plugin.name} task={task_id}")

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.runner_url}/jobs",
                    json={
                        "image": plugin.docker_image,
                        "command": cmd_args,
                        "task_id": task_id,
                        "memory_limit": "1g",
                        "cpu_count": 2,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                job = resp.json()

            job_id = job["job_id"]
            self._running_jobs[task_id] = job_id

            # Poll for completion
            result = await self._wait_for_job(job_id)
            self._running_jobs.pop(task_id, None)

            if result["status"] == "completed":
                return EngineResult(plugin.name, True, output_path=result.get("output_dir", ""),
                                    error=result.get("stderr_summary", ""), job_id=job_id)
            else:
                return EngineResult(plugin.name, False, output_path=result.get("output_dir", ""),
                                    error=result.get("error", "") or result.get("stderr_summary", "Scan failed"), job_id=job_id)

        except httpx.HTTPStatusError as e:
            return EngineResult(plugin.name, False, error=f"Scan runner rejected: {e.response.text[:500]}")
        except httpx.ConnectError:
            return EngineResult(plugin.name, False, error="Scan runner unreachable — is the scan-runner service running?")
        except Exception as e:
            return EngineResult(plugin.name, False, error=str(e))

    async def _wait_for_job(self, job_id: str, timeout: int = 3600) -> dict:
        """Poll scan-runner for job completion."""
        headers = {}
        if self.runner_secret:
            headers["X-Runner-Secret"] = self.runner_secret

        elapsed = 0
        interval = 3
        async with httpx.AsyncClient(timeout=15) as client:
            while elapsed < timeout:
                try:
                    resp = await client.get(f"{self.runner_url}/jobs/{job_id}", headers=headers)
                    data = resp.json()
                    if data["status"] in ("completed", "failed", "cancelled"):
                        return data
                except Exception:
                    pass
                await asyncio.sleep(interval)
                elapsed += interval
                if elapsed > 60:
                    interval = 10

        return {"status": "failed", "error": f"Job timed out after {timeout}s"}

    async def _run_local(
        self, plugin: PluginConfig, tool_cmd: str, task_id: str
    ) -> EngineResult:
        output_dir = Path(self.settings.scan_output_dir) / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        full_cmd = tool_cmd.replace("/output", str(output_dir))
        args = shlex.split(full_cmd)
        try:
            logger.info(f"Local scan starting: {plugin.name}")
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3600)
            (output_dir / "stdout.log").write_bytes(stdout)
            (output_dir / "stderr.log").write_bytes(stderr)

            if process.returncode == 0:
                return EngineResult(plugin.name, True, output_path=str(output_dir))
            else:
                return EngineResult(plugin.name, False, output_path=str(output_dir),
                                    error=stderr.decode(errors="replace")[:2000])
        except asyncio.TimeoutError:
            return EngineResult(plugin.name, False, error="Scan timed out (1 hour)")
        except Exception as e:
            return EngineResult(plugin.name, False, error=str(e))

    async def stop_engine(self, task_id: str):
        job_id = self._running_jobs.get(task_id)
        if job_id:
            try:
                headers = {}
                if self.runner_secret:
                    headers["X-Runner-Secret"] = self.runner_secret
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.delete(f"{self.runner_url}/jobs/{job_id}", headers=headers)
            except Exception:
                pass
            self._running_jobs.pop(task_id, None)

    async def stop_all(self):
        for task_id in list(self._running_jobs.keys()):
            await self.stop_engine(task_id)


orchestrator = EngineOrchestrator()
