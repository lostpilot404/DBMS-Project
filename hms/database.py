"""Oracle connection-pool wrapper. Uses python-oracledb Thin mode by default."""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator


class DatabaseNotConfigured(RuntimeError):
    """Raised when the application has no usable Oracle connection settings."""


class OracleDatabase:
    def __init__(self, user: str | None = None, password: str | None = None,
                 dsn: str | None = None, pool_min: int = 1, pool_max: int = 4,
                 pool_increment: int = 1) -> None:
        self.user = user
        self.password = password
        self.dsn = dsn
        self.pool_min = pool_min
        self.pool_max = pool_max
        self.pool_increment = pool_increment
        self._pool: Any | None = None
        self._pool_lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "OracleDatabase":
        user = os.getenv("ORACLE_USER") or None
        password = os.getenv("ORACLE_PASSWORD") or None
        dsn = os.getenv("ORACLE_DSN") or None
        if not dsn:
            host = os.getenv("ORACLE_HOST")
            service = os.getenv("ORACLE_SERVICE_NAME")
            port = os.getenv("ORACLE_PORT", "1521")
            if host and service:
                dsn = f"{host}:{port}/{service}"
        return cls(
            user=user,
            password=password,
            dsn=dsn,
            pool_min=_positive_env_int("ORACLE_POOL_MIN", 1),
            pool_max=_positive_env_int("ORACLE_POOL_MAX", 4),
            pool_increment=_positive_env_int("ORACLE_POOL_INCREMENT", 1),
        )

    @property
    def configured(self) -> bool:
        return bool(self.user and self.password and self.dsn)

    def _get_pool(self) -> Any:
        if not self.configured:
            raise DatabaseNotConfigured(
                "Oracle is not configured. Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN."
            )
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    try:
                        import oracledb
                    except ImportError as exc:  # pragma: no cover - installation issue
                        raise DatabaseNotConfigured(
                            "The python-oracledb dependency is not installed."
                        ) from exc
                    self._pool = oracledb.create_pool(
                        user=self.user,
                        password=self.password,
                        dsn=self.dsn,
                        min=self.pool_min,
                        max=self.pool_max,
                        increment=self.pool_increment,
                        getmode=oracledb.POOL_GETMODE_WAIT,
                    )
        return self._pool

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Acquire and reliably return a pooled connection."""
        pool = self._get_pool()
        connection = pool.acquire()
        try:
            yield connection
        finally:
            pool.release(connection)

    def close(self) -> None:
        """Close the pool on orderly shutdown (safe if it was never opened)."""
        with self._pool_lock:
            if self._pool is not None:
                self._pool.close()
                self._pool = None


def _positive_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
