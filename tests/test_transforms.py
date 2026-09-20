import pytest

from growth_scorer.transforms import piecewise_score, safe_div, signed_cagr


@pytest.mark.parametrize(
    "value,expected",
    [(-10, 0), (0, 0), (5, 25), (10, 50), (17.5, 75), (25, 100), (99, 100)],
)
def test_ascending_transform_boundaries(value, expected):
    assert piecewise_score(value, 0, 10, 25) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value,expected",
    [(10, 0), (6, 0), (4, 25), (2, 50), (1, 75), (0, 100), (-2, 100)],
)
def test_descending_transform_boundaries(value, expected):
    assert piecewise_score(value, 6, 2, 0) == pytest.approx(expected)


def test_missing_is_neutral_and_zero_denominator_is_missing():
    assert piecewise_score(None, 0, 1, 2) == 50
    assert safe_div(1, 0) is None


def test_negative_values_do_not_create_fake_cagr():
    assert signed_cagr(-1, 2, 3) is None
    assert signed_cagr(1, -2, 3) is None

