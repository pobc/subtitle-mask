import ctypes

import win32gui
from BlurWindow import blurWindow
from BlurWindow.blurWindow import GlobalBlur


def blur_top_level(top_level):
    top_level.update_idletasks()
    wid = top_level.winfo_id()
    real_wid = win32gui.GetParent(wid)
    # Prepare the native effect before exposing the transparent background.
    GlobalBlur(real_wid)
    top_level.wm_attributes('-transparentcolor', 'green')
    top_level.config(bg='green')


def clear_blur_top_level(top_level):
    accent = blurWindow.ACCENTPOLICY()
    accent.AccentState = 0  # ACCENT_DISABLED
    data = blurWindow.WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = 19  # WCA_ACCENT_POLICY
    data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.POINTER(ctypes.c_int))
    data.SizeOfData = ctypes.sizeof(accent)
    hwnd = win32gui.GetParent(top_level.winfo_id())
    blurWindow.SetWindowCompositionAttribute(hwnd, data)
