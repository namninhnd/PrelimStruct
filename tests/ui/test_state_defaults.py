from src.ui.state import STATE_DEFAULTS


def test_fem_preview_show_supports_default_is_false():
    assert STATE_DEFAULTS["fem_preview_show_supports"] is False
