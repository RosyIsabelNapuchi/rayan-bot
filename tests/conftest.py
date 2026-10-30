import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def fuentes():
    from rayan.data import cargar
    return cargar(ROOT / "data")


@pytest.fixture(scope="session")
def bot(fuentes):
    from rayan.bot import Rayan
    from rayan.config import Settings
    from rayan.llm import LLM
    return Rayan(fuentes, llm=LLM(Settings(llm_api_key="")), exigir_usuario=False)
