"""
SendInput diagnostic — run this, then switch to Notepad within 3 seconds.
If 'Hello' appears, SendInput works. If not, run as Administrator.
"""
import ctypes, time

KEYEVENTF_KEYUP = 0x0002
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("_input", _U)]

print(f"sizeof(INPUT) = {ctypes.sizeof(INPUT)} (expected 40 on 64-bit, 28 on 32-bit)")

def press(vk, up=False):
    flags = KEYEVENTF_KEYUP if up else 0
    extra = ctypes.c_ulong(0)
    inp = INPUT(type=1, _input=_U(ki=KEYBDINPUT(
        wVk=vk, wScan=0, dwFlags=flags, time=0,
        dwExtraInfo=ctypes.pointer(extra)
    )))
    result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    if result == 0:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"  SendInput FAILED — GetLastError={err}")
    return result

print("Switch to Notepad now. Typing in 3 seconds...")
time.sleep(3)

for vk in [0x48, 0x45, 0x4C, 0x4C, 0x4F]:  # H E L L O
    press(vk);        time.sleep(0.05)
    press(vk, up=True); time.sleep(0.05)

press(0x0D); time.sleep(0.05)
press(0x0D, up=True)

print("Done!")
