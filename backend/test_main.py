import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import json

# Mock the uinput module before importing main
sys.modules['uinput'] = MagicMock()

# Import app after mocking uinput
from main import app, LAYOUTS_FILE, save_layouts, all_layouts as main_all_layouts

# Use TestClient to test the FastAPI app
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Clear layouts before each test
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()
    main_all_layouts.clear() # Clear in-memory layouts
    yield
    # Clean up after each test
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()

@pytest.fixture
def mock_uinput():
    with patch('uinput.Device') as mock_device_class:
        mock_device_instance = MagicMock()
        mock_device_class.return_value = mock_device_instance
        yield mock_device_instance

@pytest.fixture
def test_layout_data():
    layout_name = "test_layout"
    layout_data = {
        "items": [
            {"i": "up_button", "x": 0, "y": 0, "icon": "↑", "keybinds": {"default": "ArrowUp", "player1": "ArrowUp", "player2": "w"}},
            {"i": "down_button", "x": 0, "y": 0, "icon": "↓", "keybinds": {"default": "ArrowDown", "player1": "ArrowDown", "player2": "s"}},
            {"i": "left_button", "x": 0, "y": 0, "icon": "←", "keybinds": {"default": "ArrowLeft", "player1": "ArrowLeft", "player2": "a"}},
            {"i": "right_button", "x": 0, "y": 0, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d"}},
        ]
    }
    # Manually save the layout to the global all_layouts dictionary for the test
    main_all_layouts[layout_name] = layout_data
    save_layouts(main_all_layouts)
    return layout_name, layout_data

def test_websocket_layout_keybinds_player1(mock_uinput, test_layout_data):
    layout_name, _ = test_layout_data
    # Mock the `main.keys` to include relevant uinput keys
    with patch('main.keys', [
        getattr(sys.modules['uinput'], 'KEY_UP'),
        getattr(sys.modules['uinput'], 'KEY_DOWN'),
        getattr(sys.modules['uinput'], 'KEY_LEFT'),
        getattr(sys.modules['uinput'], 'KEY_RIGHT'),
    ]):
        with client.websocket_connect(f"/ws/1?layout={layout_name}") as websocket:
            websocket.send_json({"itemId": "up_button", "action": "down"})
            websocket.send_json({"itemId": "up_button", "action": "up"})
            websocket.send_json({"itemId": "down_button", "action": "down"})
            websocket.send_json({"itemId": "down_button", "action": "up"})
            websocket.send_json({"itemId": "left_button", "action": "down"})
            websocket.send_json({"itemId": "left_button", "action": "up"})
            websocket.send_json({"itemId": "right_button", "action": "down"})
            websocket.send_json({"itemId": "right_button", "action": "up"})

            # Assert that the correct uinput events were emitted
            assert mock_uinput.emit.call_count == 8
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_UP, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_UP, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_DOWN, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_DOWN, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_LEFT, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_LEFT, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_RIGHT, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_RIGHT, 0)

def test_websocket_layout_keybinds_player2(mock_uinput, test_layout_data):
    layout_name, _ = test_layout_data
    # Mock the `main.keys` to include relevant uinput keys
    with patch('main.keys', [
        getattr(sys.modules['uinput'], 'KEY_W'),
        getattr(sys.modules['uinput'], 'KEY_S'),
        getattr(sys.modules['uinput'], 'KEY_A'),
        getattr(sys.modules['uinput'], 'KEY_D'),
    ]):
        with client.websocket_connect(f"/ws/2?layout={layout_name}") as websocket:
            websocket.send_json({"itemId": "up_button", "action": "down"})
            websocket.send_json({"itemId": "up_button", "action": "up"})
            websocket.send_json({"itemId": "down_button", "action": "down"})
            websocket.send_json({"itemId": "down_button", "action": "up"})
            websocket.send_json({"itemId": "left_button", "action": "down"})
            websocket.send_json({"itemId": "left_button", "action": "up"})
            websocket.send_json({"itemId": "right_button", "action": "down"})
            websocket.send_json({"itemId": "right_button", "action": "up"})

            # Assert that the correct uinput events were emitted for player 2's keybinds
            assert mock_uinput.emit.call_count == 8
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_W, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_W, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_S, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_S, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_A, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_A, 0)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_D, 1)
            mock_uinput.emit.assert_any_call(sys.modules['uinput'].KEY_D, 0)

