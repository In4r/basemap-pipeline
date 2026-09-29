import pytest

from basemap_pipeline.core import BBox, generate_basemap


def test_bbox_validate_ok():
    BBox(-122.5, 37.7, -122.3, 37.9).validate()


def test_bbox_validate_bad_longitude():
    with pytest.raises(ValueError):
        BBox(10.0, 37.7, -10.0, 37.9).validate()


def test_bbox_validate_bad_latitude():
    with pytest.raises(ValueError):
        BBox(-122.5, 40.0, -122.3, 37.9).validate()


def test_generate_basemap_accepts_tuple_and_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        generate_basemap((-122.5, 37.7, -122.3, 37.9))


def test_generate_basemap_rejects_invalid_bbox():
    with pytest.raises(ValueError):
        generate_basemap((-122.3, 37.7, -122.5, 37.9))  # min_lon > max_lon
