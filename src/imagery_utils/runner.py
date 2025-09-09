from __future__ import annotations
import os
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from .context import SceneCtx


def _build_args(job: Dict[str, Any], dstdir: str) -> SimpleNamespace:
	processing = job.get("processing", {})
	execution = job.get("execution", {})
	output = job.get("output", {})

	# Map job request to an argparse-like namespace expected by ortho_functions
	args = SimpleNamespace()
	# Required/commonly used
	args.epsg = processing.get("epsg")
	args.epsg_utm_nad83 = bool(processing.get("epsg_utm_nad83", False))
	args.dem = job.get("inputs", {}).get("dem")
	args.config_file = job.get("inputs", {}).get("config_file")
	args.outtype = processing.get("outtype", "Byte")
	res = processing.get("resolution")
	if isinstance(res, list) and len(res) == 1:
		res = [res[0], res[0]]
	args.resolution = res
	args.stretch = processing.get("stretch", "rf")
	args.resample = processing.get("resample", "near")
	args.tap = bool(processing.get("tap", False))
	args.rgb = bool(processing.get("rgb", False))
	args.bgrn = bool(processing.get("bgrn", False))
	args.save_temps = False
	args.wd = execution.get("scratch") or dstdir
	args.skip_warp = bool(processing.get("skip_warp", False))
	args.skip_dem_overlap_check = bool(processing.get("skip_dem_overlap_check", False))
	args.no_pyramids = bool(processing.get("no_pyramids", False))
	args.pyramid_type = processing.get("pyramid_type", "near")
	args.ortho_height = processing.get("ortho_height")
	args.threads = execution.get("threads", 1)
	# Format/compression
	args.format = output.get("format", "GTiff")
	args.gtiff_compression = output.get("gtiff_compression", "lzw")
	return args


def _find_sources(src_field: Any) -> List[str]:
	from lib import utils as _utils
	if isinstance(src_field, list):
		# Filter only valid file paths (best effort)
		return [p for p in src_field if isinstance(p, str)]
	if isinstance(src_field, str):
		# If directory or text file, reuse finder helpers
		if os.path.isdir(src_field):
			return _utils.find_images(src_field, False, __import__("lib.ortho_functions", fromlist=["exts"]).exts)
		return [src_field]
	return []


def _version_info() -> Dict[str, Any]:
	from osgeo import gdal
	return {
		"gdal_version": gdal.VersionInfo(),
	}


def run_ortho(job_request: Dict[str, Any]) -> Dict[str, Any]:
	"""Orchestrate staged ortho processing by adapting to existing library functions.

	Currently supports single-image flows by calling lib.ortho_functions.process_image
	with arguments mapped from the job request. Multi-image batching and HPC modes
	can be layered on top without changing this interface.
	"""
	from lib import ortho_functions as ofn
	from lib import utils as lutils

	inputs = job_request.get("inputs", {})
	output = job_request.get("output", {})
	dstdir = os.path.abspath(output.get("dst", os.getcwd()))
	os.makedirs(dstdir, exist_ok=True)

	start = time.time()
	ctx = SceneCtx()
	src_list = _find_sources(inputs.get("src"))
	artifacts: List[Dict[str, Any]] = []
	stages: List[Tuple[str, float]] = []

	if len(src_list) == 0:
		raise ValueError("No valid source images found in request.inputs.src")

	args = _build_args(job_request, dstdir)

	for src in src_list:
		# Prepare output info using ImageInfo (to know where the file will land)
		info = ofn.ImageInfo(src, dstdir, args.wd, args)
		t0 = time.time()
		err = ofn.process_image(src, info.dstfp, args, target_extent_geom=None)
		stages.append(("orthorectify", time.time() - t0))
		artifact = {
			"src": src,
			"dst": info.dstfp,
			"status": "ok" if err == 0 else "error",
		}
		artifacts.append(artifact)

	manifest: Dict[str, Any] = {
		"version": "0.1",
		"provenance": {
			"timings": {
				"total_sec": time.time() - start,
				"stages": [{"name": n, "sec": sec} for n, sec in stages],
			},
			"env": _version_info(),
		},
		"inputs": inputs,
		"output": output,
		"processing": job_request.get("processing", {}),
		"execution": job_request.get("execution", {}),
		"artifacts": artifacts,
	}
	return manifest
