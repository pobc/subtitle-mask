import tkinter as tk
from tkinter import ttk

import win32con
import win32gui


from helper.blur_helper import blur_top_level, clear_blur_top_level
from helper.keyboard_helper import KeyboardHelper
from helper.local_config import LocalConfig


class FloatingWindow:
    MASK_COLORS = (
        '#f0f0f0', '#202124', '#64748b', '#ef4444',
        '#f59e0b', '#22c55e', '#3b82f6',
    )

    def __init__(self, master):
        self.master = master
        self.top_level = top_level = tk.Toplevel(master)
        self.showing = True
        self.config = LocalConfig()

        self.hold_to_hide_hotkey = self.config.window_data.hotkeys['hold_to_hide']
        self.toggle_hotkey = self.config.window_data.hotkeys['toggle']
        self.hotkey_to_set = None
        self.active_hotkey_btn = None
        self.original_btn_text = None

        saved_color = self.config.window_data.mask_color
        self.mask_color = saved_color if saved_color in self.MASK_COLORS else self.MASK_COLORS[0]
        self._pointer_monitor_enabled = True
        self._pointer_inside = None
        self._hints_visible = False
        self._blur_active = False

        top_level.wm_attributes("-topmost", 1)
        top_level.overrideredirect(True)
        top_level.wm_geometry(self.config.get_geo_str())
        top_level.minsize(220, 30)

        top_level.bind('<B1-Motion>', self.dragging)
        top_level.bind('<Button-1>', self.on_mouse_down)
        top_level.bind('<ButtonRelease-1>', self.on_mouse_release)
        top_level.bind('<KeyPress>', self.on_hotkey_setup_key, add='+')

        self.keyboard_helper = KeyboardHelper(top_level)
        self.keyboard_helper.register_key_press(self.on_key_press)
        self.keyboard_helper.register_key_release(self.on_key_release)
        self.refresh_hotkey_watch()

        self.grip = ttk.Sizegrip(self.top_level, style='Mask.TSizegrip')

        self._drag_origin = None
        self._last_drag_position = None

        self.header_frame = tk.Frame(top_level)
        self.close_button = tk.Button(
            self.header_frame, text="×", command=self.terminate, borderwidth=0,
        )
        self.close_button.pack(side='right', padx=4)
        self.color_frame = tk.Frame(self.header_frame)
        self.color_frame.pack(side='left', padx=6, pady=2)
        self.color_swatches = {}
        for color in self.MASK_COLORS:
            swatch = tk.Canvas(
                self.color_frame, width=24, height=24,
                highlightthickness=0, borderwidth=0, cursor='hand2',
            )
            swatch.pack(side='left', padx=1)
            swatch.create_oval(1, 1, 23, 23, width=2, tags='selection')
            swatch.create_oval(5, 5, 19, 19, fill=color, outline='#a1a1aa')
            swatch.bind('<Button-1>', lambda event, value=color: self.set_mask_color(value))
            # Color clicks must not start the window's drag gesture.
            swatch.bind('<B1-Motion>', lambda event: 'break')
            swatch.bind('<ButtonRelease-1>', lambda event: 'break')
            self.color_swatches[color] = swatch

        self.hint_frame = tk.Frame(top_level)
        tk.Label(self.hint_frame, text="Hold").pack(side='left')
        self.hold_key_btn = tk.Button(
            self.hint_frame,
            text=f"[{self.hold_to_hide_hotkey}]",
            command=lambda: self.start_hotkey_setup('hold_to_hide'),
            borderwidth=0,
            cursor="hand2",
        )
        self.hold_key_btn.pack(side='left')
        tk.Label(self.hint_frame, text="or press").pack(side='left')
        self.toggle_key_btn = tk.Button(
            self.hint_frame,
            text=f"[{self.toggle_hotkey}]",
            command=lambda: self.start_hotkey_setup('toggle'),
            borderwidth=0,
            cursor="hand2",
        )
        self.toggle_key_btn.pack(side='left')
        tk.Label(self.hint_frame, text="to hide / show.").pack(side='left')

        self.need_blur_cb_var = tk.BooleanVar(value=self.config.window_data.need_blur)
        self.need_blur_cb = tk.Checkbutton(
            top_level,
            text="Blur mask",
            variable=self.need_blur_cb_var,
            command=self.on_need_blur_changed,
        )

        self.refresh_colors()
        self.blur()

        self.top_level.after(100, self.monitor_pointer)
        self.top_level.after(300, self.refresh_topmost)

    def dragging(self, event):
        if self._drag_origin is None:
            return

        pointer_x, pointer_y, window_x, window_y = self._drag_origin
        x = window_x + event.x_root - pointer_x
        y = window_y + event.y_root - pointer_y
        if (x, y) == self._last_drag_position:
            return

        # Tk's geometry path also refreshes the native frame on every move.
        # Move only the existing window, keeping its size and rendering state.
        hwnd = win32gui.GetParent(self.top_level.winfo_id())
        win32gui.SetWindowPos(
            hwnd, 0, x, y, 0, 0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )
        self._last_drag_position = (x, y)

    def on_mouse_down(self, event):
        if isinstance(event.widget, (tk.Button, tk.Checkbutton, ttk.Sizegrip)):
            return
        if self.hotkey_to_set:
            self.cancel_hotkey_setup()

        self._drag_origin = (
            event.x_root, event.y_root,
            self.top_level.winfo_x(), self.top_level.winfo_y(),
        )
        self._last_drag_position = self._drag_origin[2:]
        self._pointer_monitor_enabled = False
        self._pointer_inside = True
        self.show_hints()

    def on_mouse_release(self, _):
        self._drag_origin = None
        self._last_drag_position = None
        geo_obj = {
            'x': self.top_level.winfo_x(),
            'y': self.top_level.winfo_y(),
            'width': self.top_level.winfo_width(),
            'height': self.top_level.winfo_height(),
        }
        self.config.save_geo(geo_obj)

        self._pointer_monitor_enabled = True
        self._pointer_inside = self._is_pointer_inside()
        if self._pointer_inside:
            self.show_hints()
        else:
            self.hide_hints()

    def _is_pointer_inside(self):
        x, y = self.top_level.winfo_pointerxy()
        left = self.top_level.winfo_rootx()
        top = self.top_level.winfo_rooty()
        right = left + self.top_level.winfo_width()
        bottom = top + self.top_level.winfo_height()
        return left <= x < right and top <= y < bottom

    def monitor_pointer(self):
        if self._pointer_monitor_enabled:
            is_inside = self._is_pointer_inside()

            if is_inside != self._pointer_inside:
                self._pointer_inside = is_inside
                if is_inside:
                    self.show_hints()
                else:
                    self.hide_hints()

        self.top_level.after(100, self.monitor_pointer)

    def toggle(self):
        if self.showing:
            self.hide()
        else:
            self.show()

    def show(self):
        if not self.showing:
            self.top_level.attributes('-alpha', 1)
            self.showing = True

    def hide(self):
        if self.showing:
            self.top_level.attributes('-alpha', 0)
            self.showing = False

    def refresh_hotkey_watch(self):
        self.keyboard_helper.set_keys([
            self.hold_to_hide_hotkey,
            self.toggle_hotkey,
        ])

    def on_key_press(self, event):
        if self.hotkey_to_set:
            return

        if event.name == KeyboardHelper.normalize_key_name(self.toggle_hotkey):
            self.toggle()

        if event.name == KeyboardHelper.normalize_key_name(self.hold_to_hide_hotkey):
            self.hide()

    def on_key_release(self, event):
        if self.hotkey_to_set:
            return

        if event.name == KeyboardHelper.normalize_key_name(self.hold_to_hide_hotkey):
            self.show()

    def on_need_blur_changed(self):
        self.config.save_need_blur(self.need_blur_cb_var.get())
        if self._hints_visible:
            self.no_blur()
        else:
            self.blur()

    def set_mask_color(self, color):
        if self.hotkey_to_set:
            self.cancel_hotkey_setup()
        self.mask_color = color
        self.config.save_mask_color(color)
        self.refresh_colors()
        if self._hints_visible:
            self.no_blur()
        else:
            self.blur()
        return 'break'

    def refresh_colors(self):
        red, green, blue = self.top_level.winfo_rgb(self.mask_color)
        brightness = (red * 299 + green * 587 + blue * 114) / 1000 / 65535
        foreground = '#202124' if brightness > 0.55 else '#ffffff'

        def update_widget(widget):
            if isinstance(widget, (tk.Frame, tk.Label, tk.Button, tk.Checkbutton, tk.Canvas)):
                widget.configure(bg=self.mask_color)
            if isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton)):
                widget.configure(fg=foreground)
            if isinstance(widget, (tk.Button, tk.Checkbutton)):
                widget.configure(activebackground=self.mask_color, activeforeground=foreground)
            if isinstance(widget, tk.Checkbutton):
                widget.configure(selectcolor=self.mask_color)
            for child in widget.winfo_children():
                update_widget(child)

        update_widget(self.top_level)
        ttk.Style(self.top_level).configure('Mask.TSizegrip', background=self.mask_color)
        for color, swatch in self.color_swatches.items():
            swatch.itemconfigure(
                'selection', outline=foreground,
                state='normal' if color == self.mask_color else 'hidden',
            )

    def start_hotkey_setup(self, hotkey_type):
        if self.hotkey_to_set:
            self.cancel_hotkey_setup()

        self.hotkey_to_set = hotkey_type
        if hotkey_type == 'hold_to_hide':
            self.active_hotkey_btn = self.hold_key_btn
            self.original_btn_text = f"[{self.hold_to_hide_hotkey}]"
        else:
            self.active_hotkey_btn = self.toggle_key_btn
            self.original_btn_text = f"[{self.toggle_hotkey}]"

        self.active_hotkey_btn.config(text="Press a key...")
        self.top_level.focus_force()

    def cancel_hotkey_setup(self):
        if not self.hotkey_to_set:
            return

        self.active_hotkey_btn.config(text=self.original_btn_text)
        self.hotkey_to_set = None
        self.active_hotkey_btn = None
        self.original_btn_text = None

    def on_hotkey_setup_key(self, event):
        if not self.hotkey_to_set:
            return

        key_name = KeyboardHelper.key_name_from_tk_event(event)
        if key_name is None or not KeyboardHelper.supports_key(key_name):
            self.cancel_hotkey_setup()
            return "break"

        self.set_hotkey(key_name)
        return "break"

    def set_hotkey(self, key_name):
        key_name = KeyboardHelper.normalize_key_name(key_name)
        hotkey_type = self.hotkey_to_set

        if key_name == 'esc':
            self.cancel_hotkey_setup()
            return

        if (
            hotkey_type == 'hold_to_hide'
            and key_name == KeyboardHelper.normalize_key_name(self.toggle_hotkey)
        ) or (
            hotkey_type == 'toggle'
            and key_name == KeyboardHelper.normalize_key_name(self.hold_to_hide_hotkey)
        ):
            self.cancel_hotkey_setup()
            return

        if hotkey_type == 'hold_to_hide':
            self.hold_to_hide_hotkey = key_name
        else:
            self.toggle_hotkey = key_name

        self.config.save_hotkey(hotkey_type, key_name)
        self.active_hotkey_btn.config(text=f"[{key_name}]")
        self.hotkey_to_set = None
        self.active_hotkey_btn = None
        self.original_btn_text = None
        self.refresh_hotkey_watch()

    def terminate(self):
        self.keyboard_helper.stop()
        self.master.destroy()

    def show_hints(self):
        if self._hints_visible:
            return
        self._hints_visible = True
        self.header_frame.pack(side='top', fill='x')
        self.grip.place(relx=1, rely=1, anchor='se')
        self.hint_frame.pack(anchor="center")
        self.need_blur_cb.pack(anchor="center")
        self.no_blur()

    def hide_hints(self):
        if not self._hints_visible:
            return
        self._hints_visible = False
        self.header_frame.pack_forget()
        self.grip.place_forget()
        self.hint_frame.pack_forget()
        self.need_blur_cb.pack_forget()
        self.blur()

    def blur(self):
        if self.need_blur_cb_var.get():
            blur_top_level(self.top_level)
            self._blur_active = True
        else:
            self.no_blur()

    def no_blur(self):
        self.top_level.config(bg=self.mask_color)
        if self._blur_active:
            # Paint a solid background before removing the native effect.
            self.top_level.update_idletasks()
            clear_blur_top_level(self.top_level)
            self._blur_active = False
        if str(self.top_level.wm_attributes('-transparentcolor')):
            self.top_level.wm_attributes('-transparentcolor', '')

    def refresh_topmost(self):
        self.top_level.lift()
        self.top_level.attributes('-topmost', True)
        self.top_level.after(300, self.refresh_topmost)


class RootWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Subtitle Mask')
        self.floating_window = FloatingWindow(self.root)
        self.root.withdraw()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = RootWindow()
    app.run()
