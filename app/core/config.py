from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # NVIDIA API configuration
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"

    # Supported candidate models from NVIDIA API Catalog
    CANDIDATE_MODELS: List[str] = [
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3.5-bolt-e4b",
        "openai/gpt-oss-20b",
        "qwen/qwen3-next-80b-a3b-instruct",
        "meta/llama-3.1-70b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
    ]

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 2

settings = Settings()
