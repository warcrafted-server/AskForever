import pytest

from askforever.engine import guide as guide_module


@pytest.fixture(autouse=True)
def isolate_user_guide_patch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        guide_module, 'patch_guide_path', lambda: tmp_path / 'guide-patch.json')
