"""Signed browser-carried wizard state; no database or process-local session store."""

import hashlib
import json

from itsdangerous import BadData, URLSafeSerializer

from domain.creation_state import CreationState, CreationStateError

MAX_TOKEN_LENGTH = 1_000_000
MAX_STATE_BYTES = 16 * 1024 * 1024


class StateTokenSizeError(ValueError):
    """A valid creation is too large to return; retain the previous browser draft."""


class StateTokenCodec:
    """Tokens authenticate (not encrypt) the full character and undo history.

    Every instance with the same secret can continue a creation. The browser must
    retain the token: neither a character ID nor a cookie can recover it. Tokens
    can be replayed to branch a character; versions are local to that branch, not
    a global database compare-and-swap lock.
    """

    def __init__(self, secret):
        self.serializer = URLSafeSerializer(
            secret,
            salt="sotdl-browser-creation-v1",
            signer_kwargs={"digest_method": hashlib.sha256},
            serializer_kwargs={"ensure_ascii": False, "separators": (",", ":")},
        )

    def encode(self, state: CreationState) -> str:
        payload = state.to_dict()
        if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > MAX_STATE_BYTES:
            raise StateTokenSizeError("Creation is too large to carry in the browser")
        token = self.serializer.dumps(payload)
        if len(token) > MAX_TOKEN_LENGTH:
            raise StateTokenSizeError("Creation is too large to carry in the browser")
        return token

    def decode(self, token: str) -> CreationState:
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
            raise CreationStateError("Invalid creation token")
        try:
            # loads verifies the signature before decompressing/deserializing.
            payload = self.serializer.loads(token)
        except BadData as error:
            raise CreationStateError("Invalid creation token") from error
        return CreationState.from_dict(payload)
