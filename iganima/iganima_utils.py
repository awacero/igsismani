
import os
import sys
import logging

import pytz
from datetime import datetime
import json


import pandas as pd

from obspy import read
from obspy.clients.fdsn import Client
from obspy.core import AttribDict
from obspy.geodetics import gps2dist_azimuth
from obspy import Stream

from obspy import read_inventory


def read_config_file(json_file_path):
    """
    Reads a json_file and returns it as a python dict
    
    :param string json_file_path: path to a json file with configuration information
    :returns: dict
    """

    with open(json_file_path) as json_data:
        return json.load(json_data)


    
def get_event_by_id(fdsn_client,event_id):
    """ 
    Obtiene los eventos por dia 
    
    :param string fdsn_client: cliente fdsn 
    :param int start_time: hora de inicio 
    :param int end_time: hora de finalizacion 
    :return obspy.event.catalog 
    :raises Exception e: Error al obtener eventos
    """
    
    try:
        return fdsn_client.get_events(eventid=event_id,includearrivals=True,includeallorigins=False,includecomments=True)
        
    except Exception as e:
        raise Exception("Error in get_events_by_station_location: %s" %str(e))


def get_station(fdsn_client,station):

    try:

        inv = fdsn_client.get_stations(network=station['network'], station=station['station'], location=station["location"],
                                        channel=station['channel'] )
        #print(inv)
        return inv
    
    except Exception as e:
        print(f"Error while getting station info for {station}")



def picks2dataframe(event):
    """ 
    Guarda en una base de datos los picados de eventos falsos 
    
    :param list events: obspy.core.event 
    """
    
    picks_tmp = pd.DataFrame(event[0].picks)
    
    picks_tmp['station_id'] = picks_tmp.waveform_id.apply(
        lambda x: x.network_code+"."+x.station_code+"."+ (x.location_code if x.location_code else ".")+x.channel_code )
    
    picks_tmp['pick_time'] = picks_tmp['time']
    picks_tmp['network'] = picks_tmp.waveform_id.apply(lambda x: x.network_code)
    picks_tmp['station'] = picks_tmp.waveform_id.apply(lambda x: x.station_code)
    picks_tmp['location'] = picks_tmp.waveform_id.apply(lambda x: x.location_code if x.location_code else "")
    picks_tmp['channel'] = picks_tmp.waveform_id.apply(lambda x: x.channel_code)

    
    picks_df = picks_tmp[['station_id','pick_time','network','station','location','channel']]
    return picks_df
    




def attach_coordinates(fdsn_client,trace ):
    """
    Add coordinates info got from FDSN server as an atribDict in a trace object.  
    
    :param obspy.fdsn.client fdsn_client: client to connect to a FDSN server
    :param obspy.trace trace: waveform data
    :returns: obspy.trace with latitude, longitude and elevation attached as coordinates dict. 
    :raises Exception e: Log if fails to get data  
    """
    try:
        station_info=fdsn_client.get_stations(network=trace.stats.network,station=trace.stats.station,channel=trace.stats.channel,level="channel",format=None)       
        trace.stats.coordinates=AttribDict({'latitude':station_info[0][0][0].latitude,'longitude':station_info[0][0][0].longitude,'elevation':station_info[0][0][0].elevation})
        
        return trace
    
    except Exception as e:
        logging.info("Fail to get data for %s. Error was: %s" %(trace,str(e)))




def attach_coordinates_from_inventory(xml_inventory, trace):
    """
    Add coordinates info got from an XML inventory as an AttribDict in a trace object.

    :param str xml_inventory: Path to the XML inventory file
    :param obspy.trace.Trace trace: waveform data
    :returns: obspy.trace.Trace with latitude, longitude, and elevation attached as coordinates dict.
    :raises Exception: Logs if fails to get data
    """
    try:
        # Leer el inventario XML
        inventory = read_inventory(xml_inventory)
        
        # Encontrar la información de la estación específica
        network_code = trace.stats.network
        station_code = trace.stats.station
        location_code = trace.stats.location
        channel_code = trace.stats.channel

        # Obtener la estación y el canal específicos
        station = inventory.select(network=network_code, station=station_code, location=location_code, channel=channel_code)
        if not station:
            raise ValueError("No station found in inventory for the trace.")
        
        # Obtener la primera (y probablemente única) estación y canal
        station = station[0][0]
        channel = station.channels[0]

        # Añadir la información de las coordenadas a la traza
        trace.stats.coordinates = AttribDict({
            'latitude': channel.latitude,
            'longitude': channel.longitude,
            'elevation': channel.elevation
        })
        
        return trace
    
    except Exception as e:
        logging.info("Failed to get data for %s. Error was: %s" % (trace.id, str(e)))
        raise


def create_stations_dict(station_set, inventory):
    # Crear un mapeo de las estaciones en el inventario
    inventory_mapping = {}
    for net in inventory:
        for sta in net:
            inventory_mapping[(net.code, sta.code)] = sta

    # Crear el diccionario de información de la estación
    station_info_dict = {}
    # Opcionalmente, si prefieres una lista de diccionarios
    station_info_list = []

    # Iterar sobre el conjunto de estaciones y buscar sus coordenadas usando el mapeo
    for station_identifier in station_set:
        network_code, station_code = station_identifier.split('.')
        station_tuple = (network_code, station_code)

        # Verificar si la estación existe en el mapeo
        if station_tuple in inventory_mapping:
            station = inventory_mapping[station_tuple]

            # Asumiendo que la estación solo tiene una ubicación y un canal
            latitude = station.latitude
            longitude = station.longitude
            elevation = station.elevation

            # Guardar en el diccionario con el nombre de la estación como clave
            station_info_dict[station_code] = {
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation
            }

            # O agregar un nuevo diccionario a la lista para cada estación
            station_info_list.append({
                'station_id': station_identifier,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation
            })

    # Devolver el diccionario o la lista de diccionarios
    return station_info_dict, station_info_list


def attach_distance_dict(station_dict, event):

    """
    Attach distance to event in a station dictionary
    
    :param dictionary : dict object
    :param obspy.event event: obspy event object 
    :returns python dict with distance parameter
    """
    
    distance=gps2dist_azimuth(station_dict["latitude"],station_dict["longitude"] \
                              , event.preferred_origin().latitude, event.preferred_origin().longitude)
    
    station_dict['distance']=distance[0]
    return station_dict






def attach_distance(trace, event):
    """
    Attach distance to event as an atribDict in trace
    
    :param obspy.trace trace: obspy trace object
    :param obspy.event event: obspy event object 
    :returns obspy.trace attached with distance parameter
    """
    
    distance=gps2dist_azimuth(trace.stats.coordinates.latitude,trace.stats.coordinates.longitude \
                              , event.preferred_origin().latitude, event.preferred_origin().longitude)
    
    trace.stats['distance']=distance[0]
    return trace


def connect_fdsn(servidor_fdsn,port):
    """
    Connect to a FDSNWS server
    
    :param string servidor_fdsn: Hostname or IP of the FDSN server
    :param int port: Port number to connect to. 
    :returns obspy.clients.fdsn 
    :raises Exception e: Log if the connection couldn't be stablished and exit. 
    """
    logging.info("Connect to FDSNWS")
    try:
        client=Client("http://%s:%s" %(servidor_fdsn,port))
        return client
    except Exception as e:
        logging.info(f"Error while connecting to FDSN: {servidor_fdsn},{port}. Error was: {e}")
        raise Exception(f"Error while connecting to FDSN: {servidor_fdsn},{port}. Error was: {e}")



def create_station_set(stream_list):
    """
    Create a python set of stations
    
    :param python.list stream_list: list of streams
    :returns python set 
    """
    
    logging.info("Create a set of stations")
    station_list=[]
    for stream in stream_list:
        station_list.append(stream[0].stats.station)
    station_set=set(station_list)
    return station_set

def add_extra_parameters(fdsn_client,stream_list,event):
    """
    Add peak values, coordinates and distance to each stream in a list
    
    :param python.list stream_list: list of streams
    :param obspy.event event: event object 
    :returns list of traces with extra parameters. 
    """
    
    logging.info("Add extra parameters like distance, pga, etc.")
    
    trace_list=[]
    for stream in stream_list:
        trace_temp=stream[0]
        trace_temp=attach_coordinates(fdsn_client,trace_temp)
        trace_temp=attach_distance(trace_temp, event) 
        trace_list.append(trace_temp)
        
    return trace_list



def order_trace_list_by_distance(trace_list,plot_channel):
    """
    Return a trace list ordered by distance to an event
    
    :param list trace_list: list of obspy.traces
    :param string plot_channel: channel's name to plot
    :returns ordered trace_list
    """
    
    logging.info("Order traces by distance to the event.")
    
    station_dist_dict={}
    for trace in trace_list:
        station_dist_dict.update({"%s" %trace.stats.station : trace.stats.distance})
    
    temp_list=[]
    for key in sorted(station_dist_dict,key=station_dist_dict.get,reverse=False):
        temp_list.append(key)
    
    trace_by_distance=[]
    for station in temp_list:
        for trace in trace_list:
            if trace.stats.station==station and trace.stats.channel==plot_channel:
                trace_by_distance.append(trace)

    return trace_by_distance

def status(stat):
    """
    Take an ``stat`` string and return the same stat string with reassigned value.

    :param stat: String
    :type stat: str
    :returns: stat
    :rtype: str
    """
    if stat == 'automatic':
        stat = 'Preliminar'
    elif stat == 'manual' or stat == 'confirmed':
        stat = 'Revisado'
    else:
        stat = '-'
    return stat


def get_local_datetime(datetime_utc):
    """
    Take a ``datetime_utc_str`` string and return a ``datetime_EC string``.

    :param datetime_utc_str: String
    :type datetime_utc_str: str
    :returns: datetime_EC
    :rtype: date_time
    """
    # REPLACE BY A CONFIG PARAMETER

    local_zone = pytz.timezone('America/Guayaquil')
   
    datetime_EC = datetime_utc.replace(tzinfo=pytz.utc).astimezone(local_zone)
    return datetime_EC





def event2dict(event_object):

    event_d={}
    origin = event_object.preferred_origin() or event_object.origins[0]
    event_d['magnitude'] = round(event_object.preferred_magnitude().mag,2)
    event_d['latitude'] = round(origin.latitude,4)
    event_d['longitude'] = round(origin.longitude,4)
    event_d['depth'] = round(origin.depth/1000,1)
    event_d['datetime'] = origin.time.datetime 
    event_d["author"] = origin.creation_info.author
    event_d["event_id"] = event_object.resource_id.id.split("/")[2]

    try:
        event_d["status"] = origin.evaluation_status
    except:
        event_d["status"] = "automatic"

        
    event_d["status"] = status(event_d['status'])
    event_d["time_local"] = get_local_datetime(event_d['datetime']).strftime('%Y-%m-%d %H:%M:%S')


    return event_d

def event2dataframe(event_list):

    #author, lat, lon ,depth
    temp_list = []
    for event in event_list:
        event_d = {}
        origin = event.preferred_origin() or event.origins[0]
        event_d['latitude'] = round(origin.latitude,4)
        event_d['longitude'] = round(origin.longitude,4)
        event_d['depth'] = round(origin.depth,4)
        event_d['datetime'] = origin.time.datetime 
        event_d["author"] = origin.creation_info.author
        if origin.method_id:
            method = origin.method_id.id.split('/')[-1]
        else:
            method = None
        event_d["method"] = None
        if origin.earth_model_id:
            model = origin.earth_model_id.id.split('/')[-1]
        else:
            model = None
        event_d["model"] = None
        if origin.quality:
            azimuthal_gap = origin.quality.azimuthal_gap
        else:
            azimuthal_gap = None
        event_d["azimuthal_gap"] = azimuthal_gap

        event_d["creation_time"] = origin.time.datetime.isoformat()

        if origin.evaluation_status:
            orig_eval_status = origin.evaluation_status
        else:
            orig_eval_status = None
        event_d['evaluation_status'] = orig_eval_status
        
        if event.magnitudes:
            magnitude = event.preferred_magnitude() or event.magnitudes[0]
            magnitude_value = round(magnitude.mag,4)
            magnitude_type = magnitude.magnitude_type
        else:
            magnitude_value= None
            magnitude_type = None
        
        event_d['magnitude_value'] = magnitude_value
        event_d['magnitude_type'] = magnitude_type

        if event.event_type:
            e_type=event.event_type
            event_type=e_type.replace(" ","_")
        else:
            #event_type="not_set"  
            event_type = None
        
        event_d['event_type'] = event_type

        if event.comments:
            comment = event.comments[0].text
        else:
            comment = None
        event_d['comment'] = comment

        earthquake_name = None
        region_name =  None
        
        if event.event_descriptions:
            for e_d in event.event_descriptions:
                if e_d.type == 'earthquake name':
                    earthquake_name = e_d.text

                elif e_d.type == 'region name':
                    region_name = e_d.text        
        
        event_d['earthquake_name'] = earthquake_name
        #event_d['region_name'] = region_name
        event_d['event_id'] = event['resource_id'].id[-13:]
        event_d['origins_count'] = len(event.origins)
        event_d['picks_mean'] = int(len(event.picks)/event_d['origins_count'])
        #event_d['magnitudes_count'] = len(event.magnitudes)
        event_d['auxiliar_value'] = 1
        temp_list.append(event_d)
    
    event_df = pd.DataFrame(temp_list)
    event_df.set_index('datetime',inplace=True)
    return event_df