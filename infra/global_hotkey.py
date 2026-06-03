import ctypes
import ctypes.wintypes
from PySide6.QtCore import QAbstractNativeEventFilter


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WM_HOTKEY = 0x0312

MOD_NAME_MAP = {
    'CTRL': MOD_CONTROL,
    'SHIFT': MOD_SHIFT,
    'ALT': MOD_ALT,
    'WIN': MOD_WIN,
}


def parse_hotkey_string(s):
    if not s:
        return MOD_CONTROL | MOD_SHIFT, ord('L')
    keys = [k.strip() for k in s.split('+')]
    modifiers = 0
    vk = None
    for k in keys:
        upper = k.upper()
        if upper in MOD_NAME_MAP:
            modifiers |= MOD_NAME_MAP[upper]
        elif len(k) == 1:
            vk = ord(k.upper())
    if vk is None:
        vk = ord('L')
    if modifiers == 0:
        modifiers = MOD_CONTROL | MOD_SHIFT
    return modifiers, vk


def hotkey_to_display(modifiers, vk):
    parts = []
    if modifiers & MOD_CONTROL:
        parts.append('Ctrl')
    if modifiers & MOD_SHIFT:
        parts.append('Shift')
    if modifiers & MOD_ALT:
        parts.append('Alt')
    if modifiers & MOD_WIN:
        parts.append('Win')
    parts.append(chr(vk).upper())
    return '+'.join(parts)


class GlobalHotkey(QAbstractNativeEventFilter):
    _next_id = 1

    def __init__(self, callback, modifiers=MOD_CONTROL | MOD_SHIFT, vk=ord('L'), hotkey_id=None):
        super().__init__()
        self.callback = callback
        self._registered = False
        self._modifiers = modifiers
        self._vk = vk
        if hotkey_id is not None:
            self._hotkey_id = hotkey_id
        else:
            self._hotkey_id = GlobalHotkey._next_id
            GlobalHotkey._next_id += 1

    def register(self):
        if self._registered:
            return True
        user32 = ctypes.windll.user32
        result = user32.RegisterHotKey(None, self._hotkey_id, self._modifiers, self._vk)
        if result:
            self._registered = True
            return True
        return False

    def reregister(self, modifiers, vk):
        self.unregister()
        self._modifiers = modifiers
        self._vk = vk
        return self.register()

    def unregister(self):
        if not self._registered:
            return
        user32 = ctypes.windll.user32
        user32.UnregisterHotKey(None, self._hotkey_id)
        self._registered = False

    def nativeEventFilter(self, event_type, message):
        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
            self.callback()
            return True, 0
        return False, 0