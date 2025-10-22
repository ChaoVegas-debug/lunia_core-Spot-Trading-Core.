from __future__ import annotations

import json

import pytest
from app.ai.research.feature_catalog import FeatureCatalog, FeatureCatalogError


def test_feature_catalog_lists_new_features(tmp_path):
    catalog_path = tmp_path / "features.yaml"
    catalog_path.write_text(
        "features:\n  sample:\n    description: demo\n    metrics: []\n",
        encoding="utf-8",
    )
    catalog = FeatureCatalog(catalog_path)
    assert catalog.list_features() == ["sample"]


def test_feature_catalog_error_for_missing_root(tmp_path):
    catalog_path = tmp_path / "features.yaml"
    catalog_path.write_text("{}", encoding="utf-8")
    catalog = FeatureCatalog(catalog_path)
    with pytest.raises(FeatureCatalogError):
        catalog.load()


def test_feature_catalog_json_serialisation():
    catalog = FeatureCatalog()
    payload = json.loads(catalog.to_json())
    assert "kalman_level" in payload
    assert payload["hmm_regime"]["metrics"][0]["name"] == "hmm_high_vol_prob"
