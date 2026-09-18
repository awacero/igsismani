from iganima.iganima_utils import connect_fdsn


def test_connect_fdsn():
    client = connect_fdsn("service.iris.edu", 80)

    assert client is not None




from obspy.clients.fdsn import Client

from iganima.iganima_utils import get_event_by_id


def test_get_event_by_id():

    client = Client("ISC")

    #events = client.get_events(eventid=600860404)
    events = get_event_by_id(client, 600860404)
    assert len(events) == 1

    event = events[0]

    assert event.origins
    assert event.magnitudes

    origin = event.preferred_origin()

    assert round(origin.latitude, 3) == 2.238
    assert round(origin.longitude, 3) == 93.014

    magnitude = event.preferred_magnitude()

    assert round(magnitude.mag, 1) == 8.5