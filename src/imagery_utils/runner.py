from __future__ import annotations
from typing import Any, Dict

from .context import SceneCtx


def run_ortho(job_request: Dict[str, Any]) -> Dict[str, Any]:
	"""Orchestrate staged ortho processing (stub).
	Validates and maps job_request into staged calls. For now, returns a noop manifest.
	"""
	ctx = SceneCtx()
	manifest: Dict[str, Any] = {
		"version": "0.0-stub",
		"inputs": job_request.get("inputs", {}),
		"output": job_request.get("output", {}),
		"processing": job_request.get("processing", {}),
		"execution": job_request.get("execution", {}),
		"provenance": {
			"scene": {
				"sensor": ctx.sensor,
				"epsg": ctx.epsg,
				"chosen_dem": ctx.chosen_dem,
				"param_hash": ctx.param_hash,
			},
		}
	}
	return manifest
