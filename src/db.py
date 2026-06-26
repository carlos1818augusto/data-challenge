from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL


load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "35.199.115.174")
    port: int = int(os.getenv("DB_PORT", "3306"))
    database: str = os.getenv("DB_NAME", "looqbox-challenge")
    user: str = os.getenv("DB_USER", "looqbox-challenge")
    password: str | None = os.getenv("DB_PASSWORD")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        config = cls()
        if not config.password:
            raise RuntimeError(
                "DB_PASSWORD is required. Copy .env.example to .env and fill the password, "
                "or export DB_PASSWORD before running the scripts."
            )
        return config


def get_engine(config: DatabaseConfig | None = None) -> Engine:
    config = config or DatabaseConfig.from_env()
    url = URL.create(
        "mysql+pymysql",
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.database,
    )
    return create_engine(url, pool_pre_ping=True)
