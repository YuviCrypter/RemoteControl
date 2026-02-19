import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uinput
import json
from pathlib import Path

app = FastAPI()

# Allow your React dev server to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layouts management
LAYOUTS_FILE = Path("layouts.json")
all_layouts = {}

# Load layouts from file on startup
def load_layouts():
    if LAYOUTS_FILE.exists():
        try:
            with open(LAYOUTS_FILE, "r") as f:
                file_content = f.read() # Read content
                print(f"DEBUG: Reading layouts.json content: {file_content[:500]}...") # Print first 500 chars
                f.seek(0) # Reset file pointer for json.load
                existing_layouts = json.load(f)
                if existing_layouts:
                    return existing_layouts
        except json.JSONDecodeError as e:
            print(f"DEBUG ERROR: layouts.json is malformed: {e}. Content starts with: {file_content[:100]}...") # More detailed error
            print(f"ERROR: layouts.json is malformed. Initializing with default layout.")
        except IOError as e:
            print(f"ERROR: Could not read layouts.json: {e}. Initializing with default layout.")
    
    # Default initial layout if file doesn't exist or is empty/invalid
    default_layouts = {
        "Arrows": {
            "items": [
                {"i": "up_button", "x": 100, "y": 0, "icon": "↑", "keybinds": {"default": "ArrowUp", "player1": "ArrowUp", "player2": "w", "player3": "i"}},
                {"i": "down_button", "x": 100, "y": 100, "icon": "↓", "keybinds": {"default": "ArrowDown", "player1": "ArrowDown", "player2": "s", "player3": "k"}},
                {"i": "left_button", "x": 0, "y": 100, "icon": "←", "keybinds": {"default": "ArrowLeft", "player1": "ArrowLeft", "player2": "a", "player3": "j"}},
                {"i": "right_button", "x": 200, "y": 100, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d", "player3": "l"}},
            ]
        },
        "default": { # Add this
            "items": [
                {"i": "up_button", "x": 100, "y": 0, "icon": "↑", "keybinds": {"default": "ArrowUp", "player1": "ArrowUp", "player2": "w", "player3": "i"}},
                {"i": "down_button", "x": 100, "y": 100, "icon": "↓", "keybinds": {"default": "ArrowDown", "player1": "ArrowDown", "player2": "s", "player3": "k"}},
                {"i": "left_button", "x": 0, "y": 100, "icon": "←", "keybinds": {"default": "ArrowLeft", "player1": "ArrowLeft", "player2": "a", "player3": "j"}},
                {"i": "right_button", "x": 200, "y": 100, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d", "player3": "l"}},
            ]
        }
    }
    try:
        save_layouts(default_layouts) # Save the default layout to file
    except IOError as e:
        print(f"CRITICAL ERROR: Could not save default layouts to layouts.json: {e}. Layouts will not be persistent.")
    return default_layouts

def save_layouts(layouts_data):
    print(f"DEBUG: Saving layouts data: {json.dumps(layouts_data, indent=4)[:500]}...") # Print data being saved
    try:
        with open(LAYOUTS_FILE, "w") as f:
            json.dump(layouts_data, f, indent=4)
    except IOError as e:
        print(f"CRITICAL ERROR: Could not write to layouts.json: {e}. Changes may not be persistent.")

@app.on_event("startup")
async def startup_event():
    global all_layouts
    all_layouts = {} # Explicitly clear before loading
    all_layouts = load_layouts()

@app.get("/layouts")
async def get_all_layouts():
    return all_layouts

@app.get("/layouts/{layout_name}")
async def get_layout(layout_name: str):
    if layout_name in all_layouts:
        return all_layouts[layout_name]
    raise HTTPException(status_code=404, detail="Layout not found")

@app.post("/layouts/{layout_name}")
async def save_layout(layout_name: str, layout_data: dict):
    all_layouts[layout_name] = layout_data
    save_layouts(all_layouts)
    return {"message": f"Layout '{layout_name}' saved successfully!"}

@app.delete("/layouts/{layout_name}")
async def delete_layout(layout_name: str):
    if layout_name == "Arrows":
        raise HTTPException(status_code=403, detail="The default 'Arrows' layout cannot be deleted.")
    if layout_name in all_layouts:
        del all_layouts[layout_name]
        save_layouts(all_layouts)
        return {"message": f"Layout '{layout_name}' deleted successfully!"}
    raise HTTPException(status_code=404, detail="Layout not found")

@app.get("/")
def read_root():
    return {"status": "Backend is running and ready for remote control."}

connected_players = set()
player_counter = 0

# Define the keys that can be simulated
# Dynamically get all possible KEY_ and BTN_ events from the uinput module
keys = [getattr(uinput, key) for key in dir(uinput) if key.startswith('KEY_') or key.startswith('BTN_')]
try:
    device = uinput.Device(keys)
except Exception as e:
    print(f"Could not initialize uinput device: {e}")
    print("Running without remote control functionality.")
    device = None

# --- Remote Control WebSocket ---
# NOTE: This application must be run with root privileges for python-uinput to work
# For example: sudo /path/to/your/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
# Also, ensure the user running the script is in the 'input' group to have permissions for /dev/uinput
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int, layout_name: str = "default"):
    await websocket.accept()
    connected_players.add(player_id)
    print(f"Player {player_id} connected. Total players: {len(connected_players)}")

    # Get the layout for this player
    current_layout_data = all_layouts.get(layout_name)
    if not current_layout_data or not current_layout_data.get("items"):
        print(f"Layout '{layout_name}' not found or empty for player {player_id}. Disconnecting.")
        await websocket.close(code=1008, reason="Layout not found or invalid")
        return

    layout_items_map = {item["i"]: item for item in current_layout_data["items"]}

    try:
        while True:
            data = await websocket.receive_json()
            item_id = data.get("itemId") # Frontend will now send itemId instead of key
            action = data.get("action")
            print(f"Received from player {player_id}: itemId={item_id}, action={action}")

            if not item_id:
                print("No itemId received, skipping.")
                continue

            layout_item = layout_items_map.get(item_id)
            if not layout_item:
                print(f"Item ID '{item_id}' not found in layout '{layout_name}'.")
                continue

            keybinds = layout_item.get("keybinds", {})
            # Determine the key to press based on player_id and fallback to default
            key_to_press = keybinds.get(f"player{player_id}") or keybinds.get("default")

            if not key_to_press:
                print(f"No keybind found for item '{item_id}' for player {player_id} or default.")
                continue

            if device:
                uinput_key_name = key_to_press.upper()
                # Handle special keys that might not directly map to KEY_ prefix
                # This needs to be more robust, potentially a mapping table for uinput
                if uinput_key_name == "ARROWUP": uinput_key_name = "UP"
                elif uinput_key_name == "ARROWDOWN": uinput_key_name = "DOWN"
                elif uinput_key_name == "ARROWLEFT": uinput_key_name = "LEFT"
                elif uinput_key_name == "ARROWRIGHT": uinput_key_name = "RIGHT"
                elif uinput_key_name == " ": uinput_key_name = "SPACE"
                elif uinput_key_name == "SHIFT": uinput_key_name = "LEFTSHIFT" # Assuming common shift
                elif uinput_key_name == "CONTROL": uinput_key_name = "LEFTCTRL" # Assuming common control
                elif uinput_key_name == "ALT": uinput_key_name = "LEFTALT" # Assuming common alt
                elif uinput_key_name == "META": uinput_key_name = "LEFTMETA" # Assuming common meta (windows/command)


                key_to_press_uinput = getattr(uinput, f"KEY_{uinput_key_name}", None)
                if not key_to_press_uinput:
                     key_to_press_uinput = getattr(uinput, uinput_key_name, None) # Try direct name if not KEY_
                
                if key_to_press_uinput and key_to_press_uinput in keys:
                    if action == "down":
                        device.emit(key_to_press_uinput, 1)  # Key press
                    elif action == "up":
                        device.emit(key_to_press_uinput, 0)  # Key release
                else:
                    print(f"Unknown or un-mapped uinput key: {uinput_key_name} (derived from '{key_to_press}')")
            else:
                print("uinput device not available. Skipping key event.")


    except WebSocketDisconnect:
        connected_players.remove(player_id)
        print(f"Player {player_id} disconnected. Total players: {len(connected_players)}")

# This part of the code is not ideal for production, but for a simple case
# it can help manage players. A better approach would be a proper session management system.
@app.post("/join")
async def join_game():
    global player_counter
    player_counter += 1
    return {"player_id": player_counter}

if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(app, host="0.0.0.0", port=8000)

