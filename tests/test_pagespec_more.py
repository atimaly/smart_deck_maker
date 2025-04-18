from smartdeck.utils.pagespec import parse_pagespec, virtual_split
import pytest

def test_empty_and_whitespace_tokens():
    # stray commas or spaces are ignored
    assert parse_pagespec(" 1 ,  , 3-4 , ", total_pages=5) == [0, 2, 3]

def test_out_of_range_pages_dropped():
    # pages beyond total_pages are silently removed
    assert parse_pagespec("1-10", total_pages=3) == [0, 1, 2]

def test_invalid_format_raises():
    with pytest.raises(ValueError):
        parse_pagespec("abc,5")

def test_virtual_split_exact():
    text = "a b c d"
    # exactly 2 words per chunk
    assert virtual_split(text, 2) == ["a b", "c d"]

def test_virtual_split_tail():
    text = "one two three"
    # final chunk shorter than N is kept
    assert virtual_split(text, 2) == ["one two", "three"]

