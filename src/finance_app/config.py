"""Configurações locais não sensíveis do aplicativo."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
APP_TITLE = "Minhas Finanças"
WINDOW_SIZE = "1100x720"
MIN_WINDOW_SIZE = (860, 560)
