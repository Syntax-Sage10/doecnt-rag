from src import user_settings


def test_api_key_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(user_settings, "settings_path", lambda: tmp_path / "s.json")
    assert user_settings.load_api_key() is None
    user_settings.save_api_key("sk-test")
    assert user_settings.load_api_key() == "sk-test"
    user_settings.clear_api_key()
    assert user_settings.load_api_key() is None

def test_theme_roundtrip_and_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(user_settings, "settings_path", lambda: tmp_path / "s.json")
    assert user_settings.load_theme() == "Auto"
    user_settings.save_theme("Dark")
    assert user_settings.load_theme() == "Dark"
    user_settings.save_theme("bogus")
    assert user_settings.load_theme() == "Auto"