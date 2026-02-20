import pytest
import sys
import json
import ctypes
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app, LAYOUTS_FILE, save_layouts, all_layouts as main_all_layouts, KEY_MAP

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def clean_layouts():
    """Reset layouts file and in-memory dict around every test."""
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()
    main_all_layouts.clear()
    yield
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()


@pytest.fixture
def mock_send_input():
    """Patch the low-level SendInput call so tests never inject real keys."""
    with patch("main._SendInput") as mock_si:
        yield mock_si


@pytest.fixture
def test_layout_data():
    layout_name = "test_layout"
    layout_data = {
        "items": [
            {"i": "up_button",    "x": 0, "y": 0, "icon": "↑", "keybinds": {"default": "ArrowUp",    "player1": "ArrowUp",    "player2": "w"}},
            {"i": "down_button",  "x": 0, "y": 0, "icon": "↓", "keybinds": {"default": "ArrowDown",  "player1": "ArrowDown",  "player2": "s"}},
            {"i": "left_button",  "x": 0, "y": 0, "icon": "←", "keybinds": {"default": "ArrowLeft",  "player1": "ArrowLeft",  "player2": "a"}},
            {"i": "right_button", "x": 0, "y": 0, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d"}},
        ]
    }
    # Register under both the custom name AND "default" so TestClient WS
    # (which doesn't forward query params) still finds the layout.
    main_all_layouts[layout_name] = layout_data
    main_all_layouts["default"]   = layout_data
    save_layouts(main_all_layouts)
    return layout_name, layout_data


# ── WebSocket tests ───────────────────────────────────────────────────────────
def test_websocket_player1_arrow_keys(mock_send_input, test_layout_data):
    """Player 1 uses ArrowUp/Down/Left/Right — SendInput fires once per event.

    Note: Starlette TestClient does not forward WS URL query params to FastAPI
    query-param dependencies, so we connect without a layout param and rely on
    the fixture having pre-populated all_layouts['default'].
    """
    with client.websocket_connect("/ws/1") as ws:
        for item_id in ["up_button", "down_button", "left_button", "right_button"]:
            ws.send_json({"itemId": item_id, "action": "down"})
            ws.send_json({"itemId": item_id, "action": "up"})

    # 4 buttons × 2 events = 8 SendInput calls
    assert mock_send_input.call_count == 8


def test_websocket_player2_wasd_keys(mock_send_input, test_layout_data):
    """Player 2 uses WASD — SendInput fires the correct number of times."""
    with client.websocket_connect("/ws/2") as ws:
        for item_id in ["up_button", "down_button", "left_button", "right_button"]:
            ws.send_json({"itemId": item_id, "action": "down"})
            ws.send_json({"itemId": item_id, "action": "up"})

    assert mock_send_input.call_count == 8


def test_websocket_unknown_item_skipped(mock_send_input, test_layout_data):
    """Unknown item IDs should be silently ignored — no SendInput call."""
    with client.websocket_connect("/ws/1") as ws:
        ws.send_json({"itemId": "nonexistent_button", "action": "down"})

    assert mock_send_input.call_count == 0


def test_websocket_invalid_layout_closes_silently(mock_send_input):
    """Connecting with a non-existent layout should close the WS without sending keys."""
    # all_layouts is empty thanks to clean_layouts fixture
    with client.websocket_connect("/ws/1?layout=does_not_exist") as ws:
        # The server closes immediately; no exception on client in TestClient
        pass

    assert mock_send_input.call_count == 0


def test_websocket_no_item_id_skipped(mock_send_input, test_layout_data):
    """Messages without itemId should be silently skipped."""
    with client.websocket_connect("/ws/1") as ws:
        ws.send_json({"action": "down"})  # No itemId

    assert mock_send_input.call_count == 0


# ── Key-map sanity tests ──────────────────────────────────────────────────────
def test_key_map_contains_arrows():
    for k in ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]:
        assert k in KEY_MAP, f"Missing key in KEY_MAP: {k}"


def test_key_map_contains_wasd():
    for k in ["w", "a", "s", "d"]:
        assert k in KEY_MAP, f"Missing key in KEY_MAP: {k}"


def test_key_map_contains_space():
    assert " " in KEY_MAP


def test_key_map_contains_function_keys():
    for k in ["F1", "F5", "F12"]:
        assert k in KEY_MAP, f"Missing key in KEY_MAP: {k}"


# ── REST endpoint smoke tests ─────────────────────────────────────────────────
def test_root_returns_status():
    r = client.get("/")
    assert r.status_code == 200
    assert "status" in r.json()


def test_join_increments_player_id():
    r1 = client.post("/join")
    r2 = client.post("/join")
    assert r2.json()["player_id"] == r1.json()["player_id"] + 1
