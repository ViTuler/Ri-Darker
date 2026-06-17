import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "settings": {
        "monitor_interval": 2,
        "start_minimized": True,
        "run_at_startup": False,
    },
    "apps": {},
}

DEFAULT_APP_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "dark_title_bar": True,
    "window_theme": "DarkMode_Explorer",
    "title_bar_color": None,
    "border_color": None,
    "text_color": None,
}


class ConfigManager:
    """Manages reading and writing the YAML configuration file."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config.yaml",
            )
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as fh:
                loaded: Dict[str, Any] = yaml.safe_load(fh) or {}
            self.config = {**DEFAULT_CONFIG, **loaded}
            self.config.setdefault("settings", dict(DEFAULT_CONFIG["settings"]))
            self.config.setdefault("apps", {})
        else:
            self.config = {
                "settings": dict(DEFAULT_CONFIG["settings"]),
                "apps": {},
            }
            self.save()

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            yaml.dump(self.config, fh, default_flow_style=False, allow_unicode=True)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> Dict[str, Any]:
        return self.config.get("settings", dict(DEFAULT_CONFIG["settings"]))

    def update_settings(self, settings: Dict[str, Any]) -> None:
        self.config["settings"] = settings
        self.save()

    # ------------------------------------------------------------------
    # Apps
    # ------------------------------------------------------------------

    def get_apps(self) -> Dict[str, Dict[str, Any]]:
        return self.config.get("apps", {})

    def get_app_config(self, process_name: str) -> Optional[Dict[str, Any]]:
        return self.get_apps().get(process_name.lower())

    def add_app(
        self,
        process_name: str,
        app_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config.setdefault("apps", {})
        if app_config is None:
            app_config = dict(DEFAULT_APP_CONFIG)
        self.config["apps"][process_name.lower()] = app_config
        self.save()

    def update_app(self, process_name: str, app_config: Dict[str, Any]) -> None:
        self.config.setdefault("apps", {})
        self.config["apps"][process_name.lower()] = app_config
        self.save()

    def remove_app(self, process_name: str) -> None:
        apps = self.config.get("apps", {})
        apps.pop(process_name.lower(), None)
        self.save()
