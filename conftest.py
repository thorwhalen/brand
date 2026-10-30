"""Root pytest fixtures, shared by tests/ and the doctests under brand/."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_pipelines_dir(tmp_path, monkeypatch):
    """Pipeline runs in tests write to a temp dir, never the user's config folder."""
    monkeypatch.setattr("brand.pipeline.PIPELINES_DIR", str(tmp_path / "pipelines"))
