from smartdeck.utils.pagespec import parse_pagespec
import pytest

def test_basic():
    assert parse_pagespec("1-3,5") == [0, 1, 2, 4]

def test_descending_error():
    with pytest.raises(ValueError):
        parse_pagespec("4-2")

def test_all_pages():
    assert parse_pagespec(None, total_pages=3) == [0, 1, 2]
