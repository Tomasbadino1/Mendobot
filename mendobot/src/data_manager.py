"""Gestión de base de conocimiento en formato JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DataManager:
    """Carga y consulta datos base del bot."""

    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self._data: dict[str, Any] = {}

    def load(self) -> None:
        """Carga la base de conocimiento desde archivo JSON."""
        if not self.data_path.exists():
            self._data = {"careers": {}}
            return

        with self.data_path.open("r", encoding="utf-8") as file:
            self._data = json.load(file)

    def get_career(self, key: str) -> dict[str, Any] | None:
        """Retorna información de carrera por clave normalizada."""
        careers = self._data.get("careers", {})
        return careers.get(key)
