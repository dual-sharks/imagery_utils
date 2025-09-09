#!/usr/bin/env python3
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from jsonschema import validate, ValidationError


app = FastAPI(title="PGC Imagery Utils API", version="0.1.0")


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


@app.get("/health")
async def health() -> Dict[str, str]:
	return {"status": "ok"}


@app.post("/jobs/ortho")
async def submit_ortho_job(payload: Dict[str, Any]) -> JSONResponse:
	try:
		validate(instance=payload, schema=SCHEMA)
	except ValidationError as e:
		raise HTTPException(status_code=422, detail={"error": "validation_error", "message": e.message})

	job_id = str(uuid.uuid4())
	# For now, we just accept and echo; wiring to a queue/executor comes next.
	response = {
		"job_id": job_id,
		"status": "accepted",
		"inputs": payload.get("inputs", {}),
		"output": payload.get("output", {}),
		"processing": payload.get("processing", {}),
		"execution": payload.get("execution", {}),
	}
	return JSONResponse(status_code=202, content=response)
