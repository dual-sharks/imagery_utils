from __future__ import annotations
from typing import Any, Dict

from ..context import SceneCtx


def prepare(ctx: SceneCtx, params: Dict[str, Any]) -> SceneCtx:
	return ctx


def execute(ctx: SceneCtx) -> SceneCtx:
	return ctx
