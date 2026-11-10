import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "TwinNode Cell — Distributed Sensing and Actuation Supervisor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR.as_posix()}/twinnode.db"
    
    # Serial Port Settings
    SERIAL_PORT: str = "COM3"
    SERIAL_BAUDRATE: int = 115200
    SERIAL_TIMEOUT: float = 0.5
    AUTO_RECONNECT: bool = True
    
    # Operational Modes
    DEFAULT_SIMULATION_MODE: bool = True
    
    # Config Paths
    CONFIG_DIR: Path = BASE_DIR / "config"
    CONDITION_PROFILES_PATH: Path = BASE_DIR / "config" / "condition_profiles.json"
    EQ15_09_CONFIG_PATH: Path = BASE_DIR / "config" / "eq15_09_condition.json"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
