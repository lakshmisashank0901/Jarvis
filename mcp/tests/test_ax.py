from jarvis_mcp.ax import act_script, is_browser_app, page_click_script


def test_act_script_walks_nested_controls() -> None:
    script = act_script("compose", "safari")
    assert "entire contents" in script
    assert 'keystroke "f"' not in script
    assert "set frontmost to true" not in script
    assert "do JavaScript" not in script


def test_page_click_uses_safari_javascript() -> None:
    assert is_browser_app("safari")
    script = page_click_script("compose", "safari")
    assert "do JavaScript" in script
    assert "compose" in script.lower()
