"""
EQ-15-09 Engineering Condition Detector Module
Status: PENDING_CONFIRMATION

Notice: The exact physical criteria, trigger thresholds, and actuation sequence
for condition EQ-15-09 have not yet been supplied by the engineering authority.
This module provides a non-blocking configuration stub and evaluation hook.
Do NOT invent physical criteria without formal engineering confirmation.
"""

import json
from typing import Optional, Dict, Any
from pathlib import Path
from backend.app.core.config import settings

class EQ1509Detector:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or settings.EQ15_09_CONFIG_PATH
        self.config = self._load_config()
        self.sample_history = []

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[EQ-15-09] Warning: Could not read config file: {e}")
        return {
            "condition_id": "EQ-15-09",
            "name": "Engineering Condition EQ-15-09",
            "status": "PENDING_CONFIRMATION",
            "parameters": {"enabled": False}
        }

    def reload(self):
        self.config = self._load_config()

    def is_enabled(self) -> bool:
        return self.config.get("parameters", {}).get("enabled", False)

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "condition_id": "EQ-15-09",
            "status": self.config.get("status", "PENDING_CONFIRMATION"),
            "enabled": self.is_enabled(),
            "description": self.config.get("description", "Awaiting engineering confirmation."),
            "parameters": self.config.get("parameters", {}),
            "action_on_trigger": self.config.get("action_on_trigger", {})
        }

    def evaluate(self, current_telemetry: Dict[str, Any], target_setpoint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Non-blocking hook for EQ-15-09 evaluation.
        Returns a fault dictionary if triggered, or None if no fault or disabled.
        """
        if not self.is_enabled():
            return None

        # When engineering confirmation arrives, criteria will be evaluated here.
        # Currently inactive and safe by design.
        return None
