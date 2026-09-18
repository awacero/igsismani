
from obspy.clients.fdsn import Client

from iganima.iganima_utils import (
    get_event_by_id,
    event2dict,
)


def test_event2dict():

    client = Client("ISC")

    events = get_event_by_id(
        client,
        600860404
    )

    assert len(events) == 1

    event = events[0]

    result = event2dict(event)

    assert isinstance(result, dict)

    assert result["magnitude"] == 8.5
    assert result["latitude"] == 2.2376
    assert result["longitude"] == 93.0144

    assert "depth" in result
    assert "datetime" in result
    assert "author" in result
    assert "event_id" in result
    assert "status" in result
    assert "time_local" in result
    assert "local_date" in result
    assert "local_time" in result