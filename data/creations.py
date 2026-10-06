"""Owned creation storage with atomic version comparison."""

import threading
import time
from typing import Protocol
from copy import deepcopy

from domain.creation_state import CreationState


class CreationRepository(Protocol):
    def create(self, owner: str, state: CreationState) -> None: ...
    def get(self, owner: str, state_id: str) -> CreationState | None: ...
    def save(self, owner: str, state: CreationState, expected_version: int) -> bool: ...
    def list(self, owner: str) -> list[CreationState]: ...
    def pin_export(self, owner: str, state: CreationState) -> bool: ...
    def get_export(self, owner: str, state_id: str, version: int) -> dict | None: ...


class MemoryCreationRepository:
    """Local adapter; each read returns an independent deserialized snapshot."""

    def __init__(self, *, ttl: int = 3600, capacity: int = 1000, clock=time.time):
        self.ttl = ttl
        self.capacity = capacity
        self.clock = clock
        self._entries = {}
        self._exports = {}
        self._lock = threading.Lock()

    def _purge(self):
        expired = [
            key
            for key, (_, _, timestamp) in self._entries.items()
            if self.clock() - timestamp >= self.ttl
        ]
        for key in expired:
            del self._entries[key]

    def create(self, owner, state):
        with self._lock:
            self._purge()
            if state.state_id in self._entries:
                raise ValueError("Creation already exists")
            self._entries[state.state_id] = (owner, state.to_dict(), self.clock())
            while len(self._entries) > self.capacity:
                oldest = min(self._entries, key=lambda key: self._entries[key][2])
                del self._entries[oldest]

    def get(self, owner, state_id):
        with self._lock:
            self._purge()
            entry = self._entries.get(state_id)
            if entry is None or entry[0] != owner:
                return None
            return CreationState.from_dict(entry[1])

    def save(self, owner, state, expected_version):
        with self._lock:
            self._purge()
            entry = self._entries.get(state.state_id)
            if entry is None or entry[0] != owner or entry[1]["state_version"] != expected_version:
                return False
            self._entries[state.state_id] = (owner, state.to_dict(), self.clock())
            return True

    def list(self, owner):
        with self._lock:
            self._purge()
            entries = sorted(self._entries.values(), key=lambda entry: entry[2], reverse=True)
            return [
                CreationState.from_dict(state)
                for entry_owner, state, _ in entries
                if entry_owner == owner
            ]

    def pin_export(self, owner, state):
        with self._lock:
            self._purge()
            entry = self._entries.get(state.state_id)
            if not entry or entry[0] != owner or entry[1]["state_version"] != state.state_version:
                return False
            self._exports.setdefault(
                (owner, state.state_id, state.state_version),
                (deepcopy(state.hero.model_dump(mode="json")), self.clock() + self.ttl),
            )
            return True

    def get_export(self, owner, state_id, version):
        with self._lock:
            entry = self._exports.get((owner, state_id, version))
            return deepcopy(entry[0]) if entry and entry[1] > self.clock() else None
