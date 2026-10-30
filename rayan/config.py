"""Configuración desde variables de entorno (.env). Ningún secreto vive en el código."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:                                     # python-dotenv es opcional
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("RAYAN_DATA_DIR", ROOT / "data"))
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").strip()
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat").strip()
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "30"))
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "").strip()

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key) and not self.llm_api_key.upper().startswith("TU_")


settings = Settings()
