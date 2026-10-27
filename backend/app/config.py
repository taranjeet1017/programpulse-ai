"""Read AI configuration only when extraction is requested."""
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, SecretStr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"


class OpenAISettings(BaseModel):
    api_key: SecretStr | None
    model: str


def get_openai_settings() -> OpenAISettings:
    # Read only this project's file, without modifying process environment.
    values = dotenv_values(PROJECT_ROOT / ".env", interpolate=False)
    key = os.environ.get("OPENAI_API_KEY", values.get("OPENAI_API_KEY") or "").strip()
    model = os.environ.get("OPENAI_MODEL", values.get("OPENAI_MODEL") or "").strip()
    return OpenAISettings(
        api_key=SecretStr(key) if key and key != "your_api_key_here" else None,
        model=model or DEFAULT_OPENAI_MODEL,
    )
