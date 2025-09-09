#!/usr/bin/env python3
from __future__ import annotations

# Thin wrapper to preserve importable entrypoint
# while keeping root-level script for back-compat.

def main() -> None:
	from pgc_ortho import main as root_main
	root_main()

if __name__ == "__main__":
	main()
