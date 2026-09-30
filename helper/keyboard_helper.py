import ctypes
from types import SimpleNamespace


_USER32 = ctypes.windll.user32


class KeyboardHelper:
    """Poll only the configured shortcut keys instead of installing a global hook."""

    POLL_INTERVAL_MS = 30

    _KEY_VKS = {
        'ctrl': (0x11,),
        'shift': (0x10,),
        'alt': (0x12,),
        'win': (0x5B, 0x5C),
        'cmd': (0x5B, 0x5C),
        'space': (0x20,),
        'tab': (0x09,),
        'enter': (0x0D,),
        'esc': (0x1B,),
        'backspace': (0x08,),
        'delete': (0x2E,),
        'insert': (0x2D,),
        'home': (0x24,),
        'end': (0x23,),
        'page up': (0x21,),
        'page down': (0x22,),
        'left': (0x25,),
        'up': (0x26,),
        'right': (0x27,),
        'down': (0x28,),
        ';': (0xBA,),
        '=': (0xBB,),
        ',': (0xBC,),
        '-': (0xBD,),
        '.': (0xBE,),
        '/': (0xBF,),
        '`': (0xC0,),
        '[': (0xDB,),
        '\\': (0xDC,),
        ']': (0xDD,),
        "'": (0xDE,),
    }

    _ALIASES = {
        'control': 'ctrl',
        'control_l': 'ctrl',
        'control_r': 'ctrl',
        'shift_l': 'shift',
        'shift_r': 'shift',
        'alt_l': 'alt',
        'alt_r': 'alt',
        'menu': 'alt',
        'super_l': 'win',
        'super_r': 'win',
        'win_l': 'win',
        'win_r': 'win',
        'escape': 'esc',
        'return': 'enter',
        'backspace': 'backspace',
        'prior': 'page up',
        'next': 'page down',
    }

    def __init__(self, master):
        self.master = master
        self.key_press_cb = None
        self.key_release_cb = None
        self._watched = {}
        self._states = {}
        self._running = True
        self._after_id = self.master.after(self.POLL_INTERVAL_MS, self._poll)

    @classmethod
    def normalize_key_name(cls, key_name):
        key_name = str(key_name).strip().lower()
        return cls._ALIASES.get(key_name, key_name)

    @classmethod
    def _vks_for_key(cls, key_name):
        key_name = cls.normalize_key_name(key_name)

        if key_name in cls._KEY_VKS:
            return cls._KEY_VKS[key_name]

        if len(key_name) == 1:
            ch = key_name.upper()
            if 'A' <= ch <= 'Z' or '0' <= ch <= '9':
                return (ord(ch),)

        if key_name.startswith('f') and key_name[1:].isdigit():
            number = int(key_name[1:])
            if 1 <= number <= 24:
                return (0x6F + number,)

        return None

    @classmethod
    def supports_key(cls, key_name):
        return cls._vks_for_key(key_name) is not None

    @classmethod
    def key_name_from_tk_event(cls, event):
        keysym = event.keysym
        normalized = cls.normalize_key_name(keysym)

        modifier_map = {
            'ctrl': 'ctrl',
            'shift': 'shift',
            'alt': 'alt',
            'win': 'win',
            'cmd': 'win',
        }
        if normalized in modifier_map:
            return modifier_map[normalized]

        special_map = {
            'escape': 'esc',
            'esc': 'esc',
            'return': 'enter',
            'enter': 'enter',
            'backspace': 'backspace',
            'delete': 'delete',
            'insert': 'insert',
            'tab': 'tab',
            'space': 'space',
            'home': 'home',
            'end': 'end',
            'prior': 'page up',
            'next': 'page down',
            'left': 'left',
            'up': 'up',
            'right': 'right',
            'down': 'down',
        }
        if normalized in special_map:
            return special_map[normalized]

        char = getattr(event, 'char', '')
        if len(char) == 1 and char.isprintable() and not char.isspace():
            return char.lower()

        if normalized.startswith('f') and normalized[1:].isdigit():
            return normalized

        if len(normalized) == 1:
            return normalized

        return None

    def register_key_press(self, on_key_press):
        self.key_press_cb = on_key_press

    def register_key_release(self, on_key_release):
        self.key_release_cb = on_key_release

    def set_keys(self, keys):
        watched = {}
        states = {}

        for key_name in keys:
            normalized = self.normalize_key_name(key_name)
            vks = self._vks_for_key(normalized)
            if vks is None:
                continue
            watched[normalized] = vks
            states[normalized] = self._is_pressed(vks)

        self._watched = watched
        self._states = states

    @staticmethod
    def _is_pressed(vks):
        return any(_USER32.GetAsyncKeyState(vk) & 0x8000 for vk in vks)

    def _poll(self):
        if not self._running:
            return

        for key_name, vks in tuple(self._watched.items()):
            pressed = self._is_pressed(vks)
            was_pressed = self._states.get(key_name, False)

            if pressed != was_pressed:
                self._states[key_name] = pressed
                event = SimpleNamespace(name=key_name)

                if pressed and self.key_press_cb:
                    self.key_press_cb(event)
                elif not pressed and self.key_release_cb:
                    self.key_release_cb(event)

        self._after_id = self.master.after(self.POLL_INTERVAL_MS, self._poll)

    def stop(self):
        self._running = False
        if self._after_id is not None:
            try:
                self.master.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
