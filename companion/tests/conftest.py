import pytest

from askforever.engine import guide as guide_module


@pytest.fixture(autouse=True)
def isolate_user_guide_patch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        guide_module, 'patch_guide_path', lambda: tmp_path / 'guide-patch.json')


@pytest.fixture(autouse=True)
def not_wayland(monkeypatch):
    """Los tests no dependen de la sesión gráfica del equipo (captura por portal)."""
    monkeypatch.setenv('XDG_SESSION_TYPE', 'x11')
