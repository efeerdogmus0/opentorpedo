"""
config_manager.py — Save / load torpedo configurations as JSON files.

Serializes the entire Torpedo (all components) together with simulation
launch parameters into a single JSON file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from torpedo_model import Torpedo


# ═══════════════════════════════════════════════════════════════════════════
# Default paths
# ═══════════════════════════════════════════════════════════════════════════

_APP_DIR = Path.home() / ".opentorpedo"
LAST_SESSION_PATH = _APP_DIR / "last_session.json"


def _ensure_app_dir() -> None:
    _APP_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def save_config(
    path: str | Path,
    torpedo: Torpedo,
    sim_params: Dict[str, Any] | None = None,
    env_params: Dict[str, Any] | None = None,
) -> None:
    """Save torpedo configuration + parameters to a JSON file.

    Parameters
    ----------
    path        Destination file path (*.json).
    torpedo     The torpedo to serialize.
    sim_params  Launch parameters dict (velocity, angle, spring_force, duration, …).
    env_params  Environment parameters dict (water_density, cd_override, …).
    """
    data = {
        "version": 2,
        "torpedo": torpedo.to_dict(),
        "sim_params": sim_params or {},
        "env_params": env_params or {},
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config(path: str | Path) -> tuple[Torpedo, Dict[str, Any], Dict[str, Any]]:
    """Load a torpedo configuration from a JSON file.

    Returns
    -------
    (torpedo, sim_params, env_params)
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    torpedo = Torpedo.from_dict(data["torpedo"])
    sim_params = data.get("sim_params", {})
    env_params = data.get("env_params", {})
    return torpedo, sim_params, env_params


def save_last_session(torpedo: Torpedo,
                      sim_params: Dict[str, Any] | None = None,
                      env_params: Dict[str, Any] | None = None) -> None:
    """Auto-save current state to ~/.opentorpedo/last_session.json."""
    _ensure_app_dir()
    try:
        save_config(LAST_SESSION_PATH, torpedo, sim_params, env_params)
    except Exception:
        pass  # non-critical


def load_last_session() -> tuple[Torpedo, Dict[str, Any], Dict[str, Any]] | None:
    """Load the last auto-saved session, or None if unavailable."""
    if LAST_SESSION_PATH.exists():
        try:
            return load_config(LAST_SESSION_PATH)
        except Exception:
            return None
    return None
