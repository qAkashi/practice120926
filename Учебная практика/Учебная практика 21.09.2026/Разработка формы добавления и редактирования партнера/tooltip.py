import tkinter as tk

import theme


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<FocusIn>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def show(self, event=None):
        if self.window is not None or not self.widget.winfo_viewable():
            return
        self.window = tk.Toplevel(self.widget)
        self.window.withdraw()
        self.window.overrideredirect(True)
        tk.Label(
            self.window, text=self.text, font=theme.body_font,
            bg=theme.button_background, fg=theme.foreground,
            relief="solid", bd=1, padx=8, pady=5,
        ).pack()
        self.window.update_idletasks()
        left = min(
            self.widget.winfo_rootx(),
            self.widget.winfo_screenwidth() - self.window.winfo_reqwidth(),
        )
        top = self.widget.winfo_rooty() + self.widget.winfo_height() + 3
        self.window.geometry(f"+{max(0, left)}+{top}")
        self.window.deiconify()

    def hide(self, event=None):
        if self.window is not None:
            self.window.destroy()
            self.window = None
