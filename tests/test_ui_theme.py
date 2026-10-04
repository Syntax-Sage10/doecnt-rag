from src.ui_theme import cite, empty_state, marker_bar


def test_cite_converts_markers():
    assert cite("Fact [1][12].") == "Fact ⁽¹⁾⁽¹²⁾."


def test_marker_bar_clamps_and_is_numeric_only():
    assert 'width:100%' in marker_bar(1.7) and 'width:0%' in marker_bar(-1)


def test_empty_state_switches_copy():
    assert "Add a document" in empty_state(False) and "Ask your documents" in empty_state(True)

def test_theme_css_modes():
    from src.ui_theme import CSS, theme_css
    assert theme_css("Light") == CSS
    assert "color-scheme:dark" in theme_css("Dark")
    assert "prefers-color-scheme: dark" in theme_css("Auto")
    assert theme_css("<script>") == CSS            # unknown input never reaches the page

    