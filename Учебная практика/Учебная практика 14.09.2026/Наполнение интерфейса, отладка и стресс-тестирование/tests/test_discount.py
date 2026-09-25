import pytest

from partner_discount import calculate_partner_discount


@pytest.mark.parametrize(
    ("quantity", "expected"),
    [(0, 0), (9999, 0), (10000, 5), (49999, 5), (50000, 10),
     (299999, 10), (300000, 15), (300001, 15), (1000000, 15)],
)
def test_discount_boundaries(quantity, expected):
    assert calculate_partner_discount(quantity) == expected
