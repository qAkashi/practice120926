from pathlib import Path
from unittest.mock import Mock

import pytest

import ui_common
from audit_paths import ui_directory


def test_png_resources_are_loaded_as_explicit_binary_data(monkeypatch):
    images = [Mock(), Mock()]
    photo_image = Mock(side_effect=images)
    monkeypatch.setattr(ui_common.tk, "PhotoImage", photo_image)
    root = Mock()

    assert ui_common.load_resources(root) == tuple(images)

    for call, filename in zip(photo_image.call_args_list, ("company_logo.png", "app_icon.png")):
        assert call.kwargs["master"] is root
        assert call.kwargs["format"] == "png"
        assert "file" not in call.kwargs
        assert call.kwargs["data"] == (ui_directory / "resources" / filename).read_bytes()
        assert call.kwargs["data"].startswith(b"\x89PNG\r\n\x1a\n")
    root.iconphoto.assert_called_once_with(True, images[1])


def test_missing_resource_is_not_silently_ignored(monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", Mock(side_effect=FileNotFoundError("missing resource")))
    with pytest.raises(FileNotFoundError):
        ui_common.load_resources(Mock())
