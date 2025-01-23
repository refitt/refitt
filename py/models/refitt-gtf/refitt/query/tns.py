# -*- coding: utf-8 -*-
"""
Created on Sat Jun 17 01:50:02 2023

@author: blgnm
"""
import pandas as pd
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from astropy import units as u

def query_entire_tns_catalog(file_name: str = 'tns_data.zip') -> None:
    """
    Queries the Transient Name Server (TNS) for all events.

    Parameters
    ----------
    file_name : str, optional
        Name to save TNS catalog as. The default is tns_data.zip.

    Returns
    -------
    None

    """
    url='https://www.wis-tns.org/system/files/tns_public_objects/tns_public_objects.csv.zip'
    
    key='995ac22a4943f6b119de58955c5c4035f9081481'
    YOUR_BOT_ID=92366
    YOUR_BOT_NAME='REFITT_BOT'
    headers={'User-Agent':'tns_marker{"tns_id":'+str(YOUR_BOT_ID)+', "type":"bot",'\
         ' "name":"'+YOUR_BOT_NAME+'"}'}
    search_data={'api_key':key,}
    request=requests.post(url,data=search_data,headers=headers)
    
    
    with open(file_name, 'wb') as f:
        f.write(request.content)
        
    return None

def cross_match_with_tns(tns_data: pd.DataFrame, event_meta_data: pd.DataFrame) -> pd.DataFrame:
    """
    Cross matches a set of ZTF events with the entire TNS catalog

    Parameters
    ----------
    tns_data : pd.DataFrame
        Data frame containing the entire TNS catalog.
    event_meta_data : pd.DataFrame
        Data frame containing ZTF event meta data (columns=ZTF_ID, ra, dec).

    Returns
    -------
    pd.DataFrame
        Data frame with the cross matched TNS data.

    """
    
    classification = list()
    sn_name = list()
    redshift = list()
    for i in event_meta_data['ZTF_ID']:
        
        one_event_meta_data = event_meta_data[event_meta_data['ZTF_ID']==i]    
        event_ra, event_dec = one_event_meta_data['ra'].values, one_event_meta_data['dec'].values
        
        tns_ra, tns_dec = tns_data['ra'].values, tns_data['declination'].values
        
        
        
        tns_coords = SkyCoord(tns_ra*u.deg, tns_dec*u.deg)
        event_coords = SkyCoord(event_ra*u.deg, event_dec*u.deg)
        distance= tns_coords.separation(event_coords).arcsecond
        
        
        inde = np.argmin(distance)
        if distance[inde] <= 1:
            classification.append(tns_data['type'].values[np.argmin(distance)])
            sn_name.append(''.join([tns_data['name_prefix'].values[np.argmin(distance)],tns_data['name'].values[np.argmin(distance)]]))
            redshift.append(tns_data['redshift'].values[np.argmin(distance)])
        else:
            classification.append(np.nan)
            sn_name.append(np.nan)    
            redshift.append(np.nan)
    return pd.DataFrame({'classification':classification, 'TNS_name':sn_name, 'redshift':redshift, 'ZTF_ID': event_meta_data.ZTF_ID.values})








