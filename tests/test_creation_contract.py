"""Regression coverage for the current manual-creation HTTP contract.

These tests intentionally describe the compatibility boundary used by the
stateful refactor: the server owns the pending hero and accepts one action for
the current cursor only.
"""

import pytest

from main import app


def _start_manual_creation(client):
    response = client.get("/roll/human?is_random=0")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "need_choices"
    return data


def test_manual_choice_is_accepted_once_for_the_current_cursor(client, monkeypatch):
    data = _start_manual_creation(client)
    payload = {
        "selected_choices": [data["choices"][0][0]],
        "choice_cursor": data["choice_cursor"],
    }

    def fail_if_rebuilt(*args, **kwargs):
        raise AssertionError("manual confirmation rebuilt the hero")

    monkeypatch.setattr("utils.utils.build_hero", fail_if_rebuilt)

    first_response = client.post("/confirm_choices", json=payload)
    assert first_response.status_code == 200

    repeated_response = client.post("/confirm_choices", json=payload)
    assert repeated_response.status_code == 400
    assert b"Invalid choice cursor" in repeated_response.data


def test_manual_choice_rejects_action_outside_current_group(client):
    data = _start_manual_creation(client)
    submitted = dict(data["choices"][0][0])
    submitted["name"] = "not-an-option"

    response = client.post(
        "/confirm_choices",
        json={
            "selected_choices": [submitted],
            "choice_cursor": data["choice_cursor"],
        },
    )

    assert response.status_code == 400
    assert b"Invalid choice" in response.data


def test_manual_choice_rejects_stale_cursor(client):
    data = _start_manual_creation(client)
    response = client.post(
        "/confirm_choices",
        json={
            "selected_choices": [data["choices"][0][0]],
            "choice_cursor": data["choice_cursor"] + 1,
        },
    )

    assert response.status_code == 400
    assert b"Invalid choice cursor" in response.data