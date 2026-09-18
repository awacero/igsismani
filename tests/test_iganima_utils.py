
from iganima.iganima_functions import generate_circle


def test_generate_circle():
    latitude = 0
    longitude = -78
    radius = 10

    latitudes, longitudes = generate_circle(
        latitude,
        longitude,
        radius
    )

    assert len(latitudes) > 0
    assert len(longitudes) > 0
    assert len(latitudes) == len(longitudes)

    assert min(latitudes) < latitude
    assert max(latitudes) > latitude

    assert min(longitudes) < longitude
    assert max(longitudes) > longitude