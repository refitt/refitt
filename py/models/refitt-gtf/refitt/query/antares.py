# -*- coding: utf-8 -*-
"""
Created on Sat Jun 17 01:49:29 2023

@author: blgnm
"""

from antares_client.search import get_by_ztf_object_id
import pandas as pd
from refitt.query.exceptions import InvalidObjectIDError
import datetime

def validate_ztf_id(ztf_id: str) -> None:
    """
    Determines if the given ZTF ID can exist

    Parameters
    ----------
    ztf_id : str
        Unique ZTF identifier.

    Raises
    ------
    InvalidObjectIDError
        Error that raises when a ZTF ID doesn't exist.

    Returns
    -------
    None
        If valid, returns None.

    """
    
    today = datetime.date.today()
    year = int(str(today.year)[2:4])
    
    if len(ztf_id) != 12:
        raise InvalidObjectIDError(f'ZTF ID "{ztf_id}" must be 12 characters long')
    
    if ztf_id[:3] != 'ZTF':
        raise InvalidObjectIDError(f'ZTF ID "{ztf_id}" must begin with ZTF')
    
    if ztf_id[3:5].isdigit() == False:
        raise InvalidObjectIDError(f'ZTF ID "{ztf_id}" characters 3:5 must be the last two digits of the year it was observed.')
    
    if (int(ztf_id[3:5]) < 17) | (int(ztf_id[3:5]) > year): 
        raise InvalidObjectIDError(f'ZTF ID "{ztf_id}" year must fall within ZTFs operating period.')
        
    if ztf_id[5:].isalpha() == False:
         raise InvalidObjectIDError(f'ZTF ID "{ztf_id}" characters 5: must be letters.')
        
    return None



def format_antares_data(light_curve: pd.DataFrame, ztf_id: str) -> pd.DataFrame:
    """
    Formats a light curve from antares into the expected format.

    Parameters
    ----------
    light_curve : pd.DataFrame
        pre-formatted dataframe containing the light curve from antares.
    ztf_id : str
        Unique ZTF identifier.

    Returns
    -------
    light_curve : pd.DataFrame
        formatted dataframe containing the light curve from antares.

    """
    
    light_curve = light_curve[['ant_mjd', 'ant_passband', 'ant_mag', 'ant_magerr']]
    
    light_curve = light_curve.rename(columns = {'ant_mjd':'mjd', 'ant_passband':'band', 'ant_mag':'magnitude',
                                                'ant_magerr':'error'})
    
    light_curve = light_curve.dropna(subset='magnitude')
    
    light_curve['band'] = light_curve['band'].replace(['g', 'R'], ['ztfg', 'ztfr'])
    
    light_curve['object_id'] = ztf_id
    
    return light_curve

def query_antares_light_curve(ztf_id: str) -> pd.DataFrame:
    """


    Parameters
    ----------
    ztf_id : str
        Unique ZTF identifier.

    Returns
    -------
    pd.DataFrame
        Dataframe containing the light curve queried from antares.

    """
    
    validate_ztf_id(ztf_id)
    
    antares_data = get_by_ztf_object_id(ztf_id)
    
    light_curve = antares_data.lightcurve
    
    ra = antares_data.coordinates.ra.value
    dec = antares_data.coordinates.dec.value
    
    return format_antares_data(light_curve, ztf_id), ra, dec
    
    
def query_antares_light_curves(ztf_ids: list[str]) -> (list[pd.DataFrame], list[float], list[float]):
    """
    Queries antares for multiple light curves

    Parameters
    ----------
    ztf_ids : list[str]
        List of unique ZTF identifiers.

    Returns
    -------
    list
        list of data frames containing the light curves of the given ZTF IDs.

    """
    
    antares_data = [query_antares_light_curve(ztf_id) for ztf_id in ztf_ids]
    
    lc = [i[0] for i in antares_data]
    ra = [i[1] for i in antares_data]
    dec = [i[2] for i in antares_data]
    
    return pd.concat(lc).reset_index(drop=True), ra, dec
    
    
    