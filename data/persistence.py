"""Durable adapters sharing the same ownership and conditional-write contract."""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from data.creations import CreationRepository
from domain.creation_state import CreationState


class SQLiteCreationRepository:
    def __init__(self, path, *, ttl=604800, clock=time.time):
        self.path = str(path)
        self.ttl = ttl
        self.clock = clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _execute(self, connection, query, args=()):
        return connection.execute(query, args)

    def _encode(self, data):
        return json.dumps(data, ensure_ascii=False)

    def _decode(self, data):
        return json.loads(data) if isinstance(data, str) else data

    def initialize(self):
        with self._connect() as connection:
            self._execute(
                connection,
                """
                CREATE TABLE IF NOT EXISTS creations (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    version INTEGER NOT NULL, state TEXT NOT NULL,
                    updated DOUBLE PRECISION NOT NULL, expires DOUBLE PRECISION NOT NULL
                )
            """,
            )
            self._execute(
                connection,
                "CREATE INDEX IF NOT EXISTS creations_owner ON creations(owner, updated)",
            )
            self._initialize_exports(connection)

    def _initialize_exports(self, connection):
        self._execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS creation_exports (
                id TEXT NOT NULL, version INTEGER NOT NULL, owner TEXT NOT NULL,
                snapshot TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (id, version)
            )
        """,
        )

    def pin_export(self, owner, state):
        now = self.clock()
        with self._connect() as connection:
            result = self._execute(
                connection,
                """
                INSERT INTO creation_exports (id, version, owner, snapshot, expires)
                SELECT ?, ?, ?, ?, ? WHERE EXISTS (
                    SELECT 1 FROM creations
                    WHERE id = ? AND owner = ? AND version = ? AND expires > ?
                ) ON CONFLICT (id, version) DO UPDATE SET expires = excluded.expires
            """,
                (
                    state.state_id,
                    state.state_version,
                    owner,
                    self._encode(state.hero.model_dump(mode="json")),
                    now + self.ttl,
                    state.state_id,
                    owner,
                    state.state_version,
                    now,
                ),
            )
        return result.rowcount == 1

    def get_export(self, owner, state_id, version):
        with self._connect() as connection:
            row = self._execute(
                connection,
                "SELECT snapshot FROM creation_exports "
                "WHERE id = ? AND version = ? AND owner = ? AND expires > ?",
                (state_id, version, owner, self.clock()),
            ).fetchone()
        return self._decode(row[0]) if row else None

    def create(self, owner, state):
        now = self.clock()
        with self._connect() as connection:
            self._execute(
                connection,
                "INSERT INTO creations VALUES (?, ?, ?, ?, ?, ?)",
                (
                    state.state_id,
                    owner,
                    state.state_version,
                    self._encode(state.to_dict()),
                    now,
                    now + self.ttl,
                ),
            )

    def get(self, owner, state_id):
        with self._connect() as connection:
            row = self._execute(
                connection,
                "SELECT state FROM creations WHERE id = ? AND owner = ? AND expires > ?",
                (state_id, owner, self.clock()),
            ).fetchone()
        return CreationState.from_dict(self._decode(row[0])) if row else None

    def save(self, owner, state, expected_version):
        now = self.clock()
        with self._connect() as connection:
            result = self._execute(
                connection,
                """
                UPDATE creations SET state = ?, version = ?, updated = ?, expires = ?
                WHERE id = ? AND owner = ? AND version = ? AND expires > ?
            """,
                (
                    self._encode(state.to_dict()),
                    state.state_version,
                    now,
                    now + self.ttl,
                    state.state_id,
                    owner,
                    expected_version,
                    now,
                ),
            )
            return result.rowcount == 1

    def list(self, owner):
        with self._connect() as connection:
            rows = self._execute(
                connection,
                "SELECT state FROM creations WHERE owner = ? AND expires > ? ORDER BY updated DESC",
                (owner, self.clock()),
            ).fetchall()
        return [CreationState.from_dict(self._decode(row[0])) for row in rows]

    def cleanup(self):
        with self._connect() as connection:
            self._execute(
                connection, "DELETE FROM creation_exports WHERE expires <= ?", (self.clock(),)
            )
            return self._execute(
                connection, "DELETE FROM creations WHERE expires <= ?", (self.clock(),)
            ).rowcount


class PostgresCreationRepository(SQLiteCreationRepository):
    def __init__(self, url, *, ttl=604800, clock=time.time):
        self.url = url
        self.ttl = ttl
        self.clock = clock
        # Schema setup is explicit, not a write on every cold start.

    @contextmanager
    def _connect(self):
        import psycopg

        with psycopg.connect(self.url, connect_timeout=10) as connection:
            yield connection

    def _execute(self, connection, query, args=()):
        return connection.execute(query.replace("?", "%s"), args)

    def _encode(self, data):
        from psycopg.types.json import Jsonb

        return Jsonb(data)

    def _initialize_exports(self, connection):
        self._execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS creation_exports (
                id TEXT NOT NULL, version INTEGER NOT NULL, owner TEXT NOT NULL,
                snapshot JSONB NOT NULL, expires DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (id, version)
            )
        """,
        )

    def initialize(self):
        with self._connect() as connection:
            self._execute(
                connection,
                """
                CREATE TABLE IF NOT EXISTS creations (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    version INTEGER NOT NULL, state JSONB NOT NULL,
                    updated DOUBLE PRECISION NOT NULL, expires DOUBLE PRECISION NOT NULL
                )
            """,
            )
            self._execute(
                connection,
                "CREATE INDEX IF NOT EXISTS creations_owner ON creations(owner, updated)",
            )
            self._initialize_exports(connection)


def configured_repository() -> CreationRepository:
    url = os.environ.get("DATABASE_URL")
    if url:
        return PostgresCreationRepository(url)
    if os.environ.get("VERCEL"):
        raise RuntimeError(
            "DATABASE_URL must be configured for durable PostgreSQL storage on Vercel"
        )
    return SQLiteCreationRepository(
        os.environ.get("CREATION_DB_PATH", "instance/creations.sqlite3")
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Creation database maintenance")
    parser.add_argument("command", choices=["init", "cleanup"])
    command = parser.parse_args().command
    repository = configured_repository()
    if command == "init":
        repository.initialize()
        print("Creation schema initialized")
    else:
        print(f"Removed {repository.cleanup()} expired creations")
