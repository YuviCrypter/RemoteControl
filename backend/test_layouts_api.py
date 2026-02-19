import pytest
from fastapi.testclient import TestClient
from main import app, LAYOUTS_FILE, save_layouts
import json
from pathlib import Path

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup: Ensure layouts.json is clean before each test
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()
    # Ensure all_layouts in memory is also empty
    app.state.all_layouts = {}
    yield
    # Teardown: Clean up after each test
    if LAYOUTS_FILE.exists():
        LAYOUTS_FILE.unlink()

def test_get_empty_layouts():
    response = client.get("/layouts")
    assert response.status_code == 200
    assert response.json() == {}

def test_save_and_get_layout():
    layout_name = "test_layout"
    layout_data = {
        "items": [
            {"i": "1", "x": 0, "y": 0, "icon": "A", "keybinds": {"default": "a", "player1": "q"}}
        ]
    }
    response = client.post(f"/layouts/{layout_name}", json=layout_data)
    assert response.status_code == 200
    assert response.json() == {"message": f"Layout '{layout_name}' saved successfully!"}

    response = client.get(f"/layouts/{layout_name}")
    assert response.status_code == 200
    assert response.json() == layout_data

    response = client.get("/layouts")
    assert response.status_code == 200
    assert response.json() == {layout_name: layout_data}

def test_get_nonexistent_layout():
    response = client.get("/layouts/nonexistent_layout")
    assert response.status_code == 404
    assert response.json() == {"detail": "Layout not found"}

def test_delete_layout():
    layout_name = "layout_to_delete"
    layout_data = {"items": []}
    client.post(f"/layouts/{layout_name}", json=layout_data)

    response = client.delete(f"/layouts/{layout_name}")
    assert response.status_code == 200
    assert response.json() == {"message": f"Layout '{layout_name}' deleted successfully!"}

    response = client.get(f"/layouts/{layout_name}")
    assert response.status_code == 404

    response = client.get("/layouts")
    assert response.status_code == 200
    assert response.json() == {}

def test_delete_nonexistent_layout():
    response = client.delete("/layouts/nonexistent_layout")
    assert response.status_code == 404
    assert response.json() == {"detail": "Layout not found"}
