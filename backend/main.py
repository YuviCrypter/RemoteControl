import sys
import ctypes
from contextlib import asynccontextmanager
from ctypes import wintypes
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path

# ── Windows platform guard ────────────────────────────────────────────────────
if sys.platform != "win32":
    raise RuntimeError(
        "This backend uses the Windows SendInput API and must be run on Windows. "
        "For Linux, use the python-uinput branch."
    )

# ── Win32 SendInput structures ────────────────────────────────────────────────
# ── Win32 SendInput structures ────────────────────────────────────────────────
# CRITICAL: The union MUST include all three members (MOUSEINPUT, KEYBDINPUT,
# HARDWAREINPUT) so ctypes computes the correct sizeof(INPUT) == Win32's value.
# With only KEYBDINPUT, the struct is undersized and Windows silently rejects
# every SendInput call (returns 0, GetLastError() == ERROR_INVALID_PARAMETER).

KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

EXTENDED_KEYS = {
    0x25, 0x26, 0x27, 0x28,  # Arrows
    0x2D, 0x2E,               # Insert / Delete
    0x24, 0x23,               # Home / End
    0x21, 0x22,               # PageUp / PageDown
    0x5B, 0x5C,               # Win keys
    0x6F,                     # Numpad /
}

PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",   ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]

INPUT_KEYBOARD = 1
_SendInput = ctypes.windll.user32.SendInput

# Sanity-check: sizeof(INPUT) MUST be 40 on 64-bit Windows. If not, keys won't work.
_sz = ctypes.sizeof(INPUT)
print(f"[INIT] sizeof(INPUT)={_sz} {'✓ CORRECT' if _sz == 40 else '✗ WRONG — struct mismatch!'}")


KEYEVENTF_SCANCODE = 0x0008   # Use hardware scan code instead of VK code

def send_key(vk_code: int, action: str) -> None:
    """Inject a key event via Win32 SendInput using hardware scan codes.

    Scan-code mode (KEYEVENTF_SCANCODE) is required for DirectInput / Raw Input
    games, which bypass the message queue and read hardware scan codes directly.
    Regular apps (Notepad, browsers, etc.) also accept scan-code events fine.
    """
    # Convert VK code → hardware scan code automatically
    scan_code = ctypes.windll.user32.MapVirtualKeyW(vk_code, 0)  # MAPVK_VK_TO_VSC

    flags = KEYEVENTF_SCANCODE
    if vk_code in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if action == "up":
        flags |= KEYEVENTF_KEYUP

    extra = ctypes.c_ulong(0)
    inp = INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=0,           # Must be 0 when KEYEVENTF_SCANCODE is set
                wScan=scan_code,
                dwFlags=flags,
                time=0,
                dwExtraInfo=ctypes.pointer(extra),
            )
        ),
    )
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


# ── Key map: JS key name → Windows Virtual Key code ──────────────────────────
# Reference: https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
KEY_MAP: dict[str, int] = {
    # ── Arrows ──
    "ArrowLeft":  0x25,
    "ArrowUp":    0x26,
    "ArrowRight": 0x27,
    "ArrowDown":  0x28,
    # ── Common control keys ──
    "Backspace":   0x08,
    "Tab":         0x09,
    "Enter":       0x0D,
    "Shift":       0x10,
    "Control":     0x11,
    "Alt":         0x12,
    "Pause":       0x13,
    "CapsLock":    0x14,
    "Escape":      0x1B,
    " ":           0x20,  # Space
    "PageUp":      0x21,
    "PageDown":    0x22,
    "End":         0x23,
    "Home":        0x24,
    "PrintScreen": 0x2C,
    "Insert":      0x2D,
    "Delete":      0x2E,
    # ── Digits ──
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    # ── Letters (VK codes = uppercase ASCII) ──
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    # ── Uppercase letters (same VK) ──
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59,
    "Z": 0x5A,
    # ── Special / modifier ──
    "Meta":         0x5B,  # Left Win key
    "ContextMenu":  0x5D,
    "NumLock":      0x90,
    "ScrollLock":   0x91,
    "ShiftLeft":    0xA0,
    "ShiftRight":   0xA1,
    "ControlLeft":  0xA2,
    "ControlRight": 0xA3,
    "AltLeft":      0xA4,
    "AltRight":     0xA5,
    # ── Function keys ──
    "F1":  0x70, "F2":  0x71, "F3":  0x72, "F4":  0x73,
    "F5":  0x74, "F6":  0x75, "F7":  0x76, "F8":  0x77,
    "F9":  0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    # ── Punctuation / OEM keys ──
    ";":  0xBA, "=":  0xBB, ",":  0xBC, "-":  0xBD,
    ".":  0xBE, "/":  0xBF, "`":  0xC0, "[":  0xDB,
    "\\": 0xDC, "]":  0xDD, "'":  0xDE,
}


# ── Layouts persistence ───────────────────────────────────────────────────────
LAYOUTS_FILE = Path("layouts.json")
all_layouts: dict = {}

def load_layouts() -> dict:
    if LAYOUTS_FILE.exists():
        try:
            with open(LAYOUTS_FILE, "r") as f:
                existing = json.load(f)
                if existing:
                    return existing
        except (json.JSONDecodeError, IOError) as e:
            print(f"ERROR: Could not load layouts.json: {e}. Using defaults.")

    default_layouts = {
        "Arrows": {
            "items": [
                {"i": "up_button",    "x": 100, "y": 0,   "icon": "↑", "keybinds": {"default": "ArrowUp",    "player1": "ArrowUp",    "player2": "w", "player3": "i"}},
                {"i": "down_button",  "x": 100, "y": 100, "icon": "↓", "keybinds": {"default": "ArrowDown",  "player1": "ArrowDown",  "player2": "s", "player3": "k"}},
                {"i": "left_button",  "x": 0,   "y": 100, "icon": "←", "keybinds": {"default": "ArrowLeft",  "player1": "ArrowLeft",  "player2": "a", "player3": "j"}},
                {"i": "right_button", "x": 200, "y": 100, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d", "player3": "l"}},
            ]
        },
        "default": {
            "items": [
                {"i": "up_button",    "x": 100, "y": 0,   "icon": "↑", "keybinds": {"default": "ArrowUp",    "player1": "ArrowUp",    "player2": "w", "player3": "i"}},
                {"i": "down_button",  "x": 100, "y": 100, "icon": "↓", "keybinds": {"default": "ArrowDown",  "player1": "ArrowDown",  "player2": "s", "player3": "k"}},
                {"i": "left_button",  "x": 0,   "y": 100, "icon": "←", "keybinds": {"default": "ArrowLeft",  "player1": "ArrowLeft",  "player2": "a", "player3": "j"}},
                {"i": "right_button", "x": 200, "y": 100, "icon": "→", "keybinds": {"default": "ArrowRight", "player1": "ArrowRight", "player2": "d", "player3": "l"}},
            ]
        },
    }
    save_layouts(default_layouts)
    return default_layouts


def save_layouts(layouts_data: dict) -> None:
    try:
        with open(LAYOUTS_FILE, "w") as f:
            json.dump(layouts_data, f, indent=4)
    except IOError as e:
        print(f"ERROR: Could not write layouts.json: {e}")


# ── FastAPI app (lifespan replaces deprecated @on_event) ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global all_layouts
    all_layouts = load_layouts()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Layout REST endpoints ─────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"status": "Backend is running (Windows — SendInput)."}

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


# ── Player session ────────────────────────────────────────────────────────────
connected_players: set = set()
player_counter: int = 0

@app.post("/join")
async def join_game():
    global player_counter
    player_counter += 1
    return {"player_id": player_counter}


# ── WebSocket remote-control endpoint ────────────────────────────────────────
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int, layout: str = "default"):
    await websocket.accept()
    connected_players.add(player_id)

    # Self-healing: if in-memory layouts got wiped (e.g. tests ran, or lifespan issue), reload from disk
    global all_layouts
    if not all_layouts:
        print("[WS] all_layouts is empty — reloading from disk.")
        all_layouts = load_layouts()

    print(f"[WS] Player {player_id} connected | layout='{layout}' | available={list(all_layouts.keys())}")

    current_layout_data = all_layouts.get(layout)
    if not current_layout_data or not current_layout_data.get("items"):
        print(f"[WS] ERROR: Layout '{layout}' not found. Available: {list(all_layouts.keys())}. Closing.")
        await websocket.close(code=1008, reason="Layout not found or invalid")
        connected_players.discard(player_id)
        return

    layout_items_map = {item["i"]: item for item in current_layout_data["items"]}
    print(f"[WS] Layout '{layout}' OK — {len(layout_items_map)} buttons: {list(layout_items_map.keys())}")

    try:
        while True:
            data = await websocket.receive_json()
            item_id = data.get("itemId")
            action  = data.get("action")  # "down" | "up"

            if not item_id:
                continue

            layout_item = layout_items_map.get(item_id)
            if not layout_item:
                print(f"[WS] Unknown item '{item_id}' in layout '{layout}'.")
                continue

            keybinds = layout_item.get("keybinds", {})
            key_name = keybinds.get(f"player{player_id}") or keybinds.get("default")

            if not key_name:
                print(f"[WS] No keybind for item '{item_id}', player {player_id}.")
                continue

            vk_code = KEY_MAP.get(key_name)
            if vk_code is None:
                print(f"[WS] Key '{key_name}' not in KEY_MAP — add it to main.py if needed.")
                continue

            send_key(vk_code, action)
            print(f"[WS] {action.upper()} → '{key_name}' (VK={hex(vk_code)})")

    except WebSocketDisconnect:
        connected_players.discard(player_id)
        print(f"[WS] Player {player_id} disconnected. Total: {len(connected_players)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
