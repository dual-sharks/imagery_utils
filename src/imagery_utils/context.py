from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SceneCtx:
	# Immutable context carried through stages
	sensor: Optional[str] = None
	rpc: Optional[Dict[str, Any]] = None
	epsg: Optional[int] = None
	footprints_wkt: Optional[str] = None
	pixel_size: Optional[float] = None
	chosen_dem: Optional[str] = None
	param_hash: Optional[str] = None
	# Free-form bag for future needs
	meta: Dict[str, Any] = field(default_factory=dict)
