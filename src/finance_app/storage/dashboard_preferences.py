"""Persistência local do período escolhido no painel financeiro."""

import json
import os
import tempfile
from datetime import date
from pathlib import Path


class DashboardPeriodPreferences:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> tuple[date, date] | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        start = date.fromisoformat(data["start"])
        end = date.fromisoformat(data["end"])
        if start > end:
            raise ValueError("O período salvo tem uma data inicial posterior à data final.")
        return start, end

    def save(self, start: date, end: date) -> None:
        if type(start) is not date or type(end) is not date or start > end:
            raise ValueError("Informe um período válido para salvar.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    {"start": start.isoformat(), "end": end.isoformat()},
                    temporary_file,
                )
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
