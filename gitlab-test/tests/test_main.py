import pytest

from src.main import add, safe_div


def test_add():
    assert add(2, 3) == 5


def test_safe_div():
    assert safe_div(10, 2) == 5


def test_safe_div_zero():
    with pytest.raises(ValueError):
        safe_div(1, 0)

