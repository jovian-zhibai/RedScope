"""Scan Runner: isolated service that executes scan containers.
This is the ONLY component with Docker daemon access.
Backend communicates with it via HTTP API — never touches Docker directly."""

import asyncio
import os
import shlex
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="RedScope Scan Runner", version="1.0.0")

SCAN_OUTPUT_BASE = os.environ.get("SCAN_OUTPUT_DIR", "/app/output")
ALLOWED_IMAGES_PREFIX = os.environ.get("ALLOWED_IMAGES", "").split(",") if os.environ.get("ALLOWED_IMAGES") else []
RUNNER_SECRET = os.environ.get("RUNNER_SECRET", "")
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "10"))

jobs: dict[str, dict] = {}
_job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


class JobRequest(BaseModel):
    image: str
    command: list[str]
    task_id: str = ""
    memory_limit: str = "1g"
    cpu_count: int = 2


class JobResponse(BaseModel):
    job_id: str
    status: str
    output_dir: str = ""
    error: str = ""
    exit_code: int = -1


def _verify_secret(request):
    if RUNNER_SECRET:
        auth = request.headers.get("X-Runner-Secret", "")
        if auth != RUNNER_SECRET:
            raise HTTPException(403, "Invalid runner secret")


def _validate_image(image: str):
    """Only allow pre-approved images — exact repo match, any tag."""
    if not ALLOWED_IMAGES_PREFIX:
        return
    # Extract repo (before :tag)
    repo = image.split(":")[0] if ":" in image else image
    if repo not in ALLOWED_IMAGES_PREFIX:
        raise HTTPException(400, f"Image '{image}' not in allowed list. Allowed repos: {ALLOWED_IMAGES_PREFIX}")


@app.post("/jobs", response_model=JobResponse)
async def create_job(req: JobRequest, request: Request):
    import docker

    _verify_secret(request)
    _validate_image(req.image)

    # Check concurrent job limit
    active = sum(1 for j in jobs.values() if j["status"] == "running")
    if active >= MAX_CONCURRENT_JOBS:
        raise HTTPException(429, f"并发扫描数已达上限({MAX_CONCURRENT_JOBS})，请等待现有任务完成")

    job_id = req.task_id or str(uuid.uuid4())[:12]
    output_dir = Path(SCAN_OUTPUT_BASE) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    jobs[job_id] = {"status": "running", "started_at": datetime.now().isoformat(), "container_id": None}

    async def run():
        async with _job_semaphore:
            try:
                client = docker.from_env(timeout=120)
                container_name = f"rs_scan_{job_id}"

                container = client.containers.run(
                    image=req.image,
                    command=req.command,
                    name=container_name,
                    detach=True,
                    # SECURITY: host network required for nmap/masscan to work properly.
                    # Scanned containers can access host network — mitigated by read_only + cap_drop ALL.
                    network_mode="host",
                    mem_limit=req.memory_limit,
                    cpu_count=req.cpu_count,
                    read_only=True,
                    cap_drop=["ALL"],
                    tmpfs={"/tmp": ""},
                    volumes={str(output_dir.resolve()): {"bind": "/output", "mode": "rw"}},
                    auto_remove=False,
                )

                jobs[job_id]["container_id"] = container.id

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: container.wait(timeout=3600))
                exit_code = result.get("StatusCode", -1)

                stdout = container.logs(stdout=True, stderr=False)
                stderr = container.logs(stdout=False, stderr=True)
                (output_dir / "stdout.log").write_bytes(stdout)
                (output_dir / "stderr.log").write_bytes(stderr)

                container.remove(force=True)

                jobs[job_id].update({
                    "status": "completed" if exit_code == 0 else "failed",
                    "exit_code": exit_code,
                    "output_dir": str(output_dir),
                    "error": stderr.decode(errors="replace")[:2000] if exit_code != 0 else "",
                    "finished_at": datetime.now().isoformat(),
                })

            except Exception as e:
                jobs[job_id].update({"status": "failed", "error": str(e), "finished_at": datetime.now().isoformat()})
                try:
                    client = docker.from_env()
                    client.containers.get(f"rs_scan_{job_id}").remove(force=True)
                except Exception:
                    pass

    asyncio.create_task(run())
    return JobResponse(job_id=job_id, status="running", output_dir=str(output_dir))


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, request: Request):
    _verify_secret(request)
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        output_dir=job.get("output_dir", ""),
        error=job.get("error", ""),
        exit_code=job.get("exit_code", -1),
    )


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, request: Request):
    import docker
    _verify_secret(request)
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    container_id = job.get("container_id")
    if container_id:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove(force=True)
        except Exception:
            pass

    jobs[job_id]["status"] = "cancelled"
    return {"status": "cancelled"}


@app.get("/health")
async def health():
    import docker
    try:
        client = docker.from_env()
        client.ping()
        return {"status": "ok", "docker": "connected"}
    except Exception as e:
        return {"status": "degraded", "docker": "error"}
