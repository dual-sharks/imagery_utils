#!/usr/bin/env python3
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from jsonschema import validate, ValidationError


app = FastAPI(title="PGC Imagery Utils API", version="0.1.0")

# Ensure src/ is importable for imagery_utils.* in dev/container contexts
_repo_root = Path(__file__).resolve().parents[2]
_src_dir = _repo_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
	sys.path.insert(0, str(_src_dir))

try:
	from imagery_utils.runner import run_ortho as runner_run_ortho
except Exception:
	# Degrade gracefully if package not importable yet
	runner_run_ortho = None  # type: ignore


def load_schema() -> Dict[str, Any]:
	# Resolve schema path relative to this file, falling back to repo root
	schema_path = Path(__file__).resolve().parents[1] / "schemas" / "ortho_job.schema.json"
	if not schema_path.is_file():
		# Fallback: relative to CWD (e.g., /app)
		schema_path = Path(os.getcwd()) / "tools" / "schemas" / "ortho_job.schema.json"
	if not schema_path.is_file():
		raise RuntimeError(f"Schema file not found: {schema_path}")
	with open(schema_path, "r") as f:
		return json.load(f)


SCHEMA = load_schema()
_JOBS: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
async def health() -> Dict[str, str]:
	return {"status": "ok"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
	job = _JOBS.get(job_id)
	if not job:
		raise HTTPException(status_code=404, detail={"error": "not_found"})
	return JSONResponse(content=job)


@app.post("/jobs/ortho")
async def submit_ortho_job(payload: Dict[str, Any]) -> JSONResponse:
	try:
		validate(instance=payload, schema=SCHEMA)
	except ValidationError as e:
		raise HTTPException(status_code=422, detail={"error": "validation_error", "message": e.message})

	job_id = str(uuid.uuid4())
	# For now, run synchronously through the stubbed runner to generate a manifest; queue comes later.
	status = "accepted"
	manifest: Dict[str, Any] = {}
	if runner_run_ortho is not None:
		try:
			manifest = runner_run_ortho(payload)
			status = "completed"
		except Exception as e:
			status = "failed"
			manifest = {"error": str(e)}

	job_record = {
		"job_id": job_id,
		"status": status,
		"request": payload,
		"result": manifest,
	}
	_JOBS[job_id] = job_record
	code = 201 if status == "completed" else 202
	return JSONResponse(status_code=code, content=job_record)
