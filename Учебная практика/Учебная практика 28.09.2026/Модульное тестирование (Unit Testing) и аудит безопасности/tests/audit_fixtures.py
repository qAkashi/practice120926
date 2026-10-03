import gc
import logging
import tkinter as tk
from tkinter import messagebox
from unittest.mock import Mock

import pytest

from app_logging import configure_logging, logger
from audit_main_window import MainWindow


@pytest.fixture
def log_file(tmp_path):
    path = tmp_path / "app.log"
    configure_logging(path)
    yield path
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.addHandler(logging.NullHandler())


@pytest.fixture
def audited_app(monkeypatch, log_file):
    gc.collect()
    errors = Mock(return_value="ok")
    monkeypatch.setattr(messagebox, "showerror", errors)
    root = tk.Tk()
    root.withdraw()
    loader = Mock(return_value=[])
    application = MainWindow(root, loader, initial_password="", auto_start=False)
    yield application, errors, loader, log_file
    if application.editor_is_open():
        application.edit_window.close(notify=False, confirm=False)
    application.close()
    gc.collect()
