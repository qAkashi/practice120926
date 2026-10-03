import gc
import tkinter as tk
from tkinter import messagebox
from unittest.mock import Mock

import pytest

from material_main_window import MainWindow


@pytest.fixture
def calculator_app(monkeypatch):
    gc.collect()
    errors = Mock(return_value="ok")
    monkeypatch.setattr(messagebox, "showerror", errors)
    root = tk.Tk()
    root.withdraw()
    callbacks = []
    root.report_callback_exception = lambda *args: callbacks.append(args)
    application = MainWindow(root, lambda password: [], initial_password="", auto_start=False)
    yield application, errors
    if application.editor_is_open():
        application.edit_window.close(notify=False, confirm=False)
    application.close()
    gc.collect()
    assert not callbacks, callbacks
