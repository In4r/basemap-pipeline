import copy
import json

import numpy as np
import pytest

from basemap_pipeline.core import BBox, generate_basemap
from basemap_pipeline.geometry_document import (
    Polyline,
    build_document,
    confidence_score,
    line_length,
    mean_mask_probability,
)
from basemap_pipeline.validate import main as validate_main
from basemap_pipeline.validate import validate_document

PORT_JEFF = (-73.070, 40.945, -73.060, 40.953)


@pytest.fixture
def doc():
    return generate_basemap(PORT_JEFF, use_mock=True).document


def test_mock_document_is_valid_and_marked_mock(doc):
    assert validate_document(doc) == []
    assert doc["generator"]["mock"] is True
    assert doc["crs"]["units"] == "us-survey-foot"
    assert {f["class"] for f in doc["features"]} == {"lane_line", "crosswalk_edge", "curb", "median"}


def test_real_polylines_are_not_marked_mock():
    lines = [Polyline("curb", [(0.0, 0.0), (100.0, 0.0)], 0.9)]
    out = generate_basemap(PORT_JEFF, polylines=lines).document
    assert out["generator"]["mock"] is False
    assert out["features"][0]["length_ft"] == 100.0


def test_no_vectors_and_no_mock_raises():
    with pytest.raises(NotImplementedError):
        generate_basemap(PORT_JEFF)


def test_non_foot_crs_rejected():
    with pytest.raises(ValueError, match="US survey feet"):
        generate_basemap(PORT_JEFF, use_mock=True, epsg=32618)  # UTM 18N, metres


def test_writes_file_that_validates(tmp_path):
    res = generate_basemap(PORT_JEFF, use_mock=True, out_dir=str(tmp_path))
    assert res.output_path and res.output_path.startswith(str(tmp_path))
    assert validate_main([res.output_path]) == 0


def test_confidence_formula():
    assert confidence_score(0.9, 60.0) == 0.9  # long enough: probability only
    assert confidence_score(0.9, 15.0) == 0.45  # half the reference length
    assert confidence_score(1.5, 100.0) == 1.0  # clamped
    with pytest.raises(ValueError):
        confidence_score(0.9, 10.0, 0)


def test_mean_mask_probability_samples_along_line():
    prob = np.zeros((10, 10))
    prob[5, :] = 0.8  # row 5 is y in [4, 5) for a 1 ft pixel with top at y=10
    got = mean_mask_probability(prob, (0.0, 10.0), 1.0, [(0.5, 4.5), (9.5, 4.5)])
    assert got == pytest.approx(0.8)
    with pytest.raises(ValueError):
        mean_mask_probability(prob, (0.0, 10.0), 1.0, [(100.0, 100.0), (101.0, 100.0)])


def test_line_length():
    assert line_length([(0, 0), (3, 4), (3, 10)]) == 11.0


def test_unknown_class_rejected():
    with pytest.raises(ValueError):
        build_document(
            BBox(*PORT_JEFF), [Polyline("sidewalk", [(0, 0), (1, 1)], 0.5)],
            epsg=2263, crs_name="x", mock=True,
        )


def _broken(doc, mutate):
    bad = copy.deepcopy(doc)
    mutate(bad)
    return validate_document(bad)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("crs"),
        lambda d: d.update(schema_version="1"),
        lambda d: d["features"][0].update({"class": "sidewalk"}),
        lambda d: d["features"][0]["geometry"].update(coordinates=[[0, 0]]),
        lambda d: d["features"][0]["confidence"].update(score=1.5),
        lambda d: d["features"][0].update(length_ft=999999.0),
        lambda d: d["features"][1].update(id=d["features"][0]["id"]),
        lambda d: d["bbox"].update(min_lon=d["bbox"]["max_lon"]),
        lambda d: d["features"][0]["geometry"]["coordinates"][0].__setitem__(0, "x"),
    ],
)
def test_malformed_documents_fail(doc, mutate):
    assert _broken(doc, mutate) != []


def test_cli_fails_on_bad_file(tmp_path, doc):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(doc))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({**doc, "schema_version": "9"}))
    assert validate_main([str(good)]) == 0
    assert validate_main([str(good), str(bad)]) == 1
    assert validate_main([str(tmp_path / "missing.json")]) == 1
