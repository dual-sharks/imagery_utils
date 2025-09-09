#!/usr/bin/env python3
import argparse
import glob
import json
import os
import subprocess
import sys


def gdalinfo_json(path):
	cmd = ["gdalinfo", "-json", path]
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	so, se = p.communicate()
	if p.returncode != 0:
		return {"path": path, "error": se.decode("utf-8", errors="ignore")}
	try:
		data = json.loads(so.decode("utf-8"))
	except Exception as e:
		return {"path": path, "error": f"json parse error: {e}"}
	data["path"] = path
	return data


def main():
	ap = argparse.ArgumentParser(description="Collect gdalinfo -json for rasters")
	ap.add_argument("targets", nargs="+", help="Raster paths or globs")
	ap.add_argument("--out", required=True, help="Output JSON file")
	args = ap.parse_args()

	files = []
	for t in args.targets:
		files.extend(glob.glob(t))
	files = sorted(set(files))
	if not files:
		print("No targets matched", file=sys.stderr)
		sys.exit(1)

	results = [gdalinfo_json(fp) for fp in files]

	os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
	with open(args.out, "w") as f:
		json.dump({"artifacts": results}, f, indent=2)

	print(f"Wrote {len(results)} entries to {args.out}")


if __name__ == "__main__":
	main()
