# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 01:36:59 2023

@author: blgnm
"""
from refitt.query.galaxy.ned import query_closest_ned_source
from refitt.query.galaxy.sdss import query_closest_sdss_source_photoz
from refitt.query.galaxy.panstarrs import query_closest_panstarrs_source
from refitt.query.galaxy.galaxy_exceptions import NoSourcesError
import pandas as pd
import numpy as np

def cross_match_galaxies(galaxy_ra: list[float], galaxy_dec: list[float]) -> pd.DataFrame:
    """
    Evaluates the ned, sdss, and panstar query functions on a list of galaxies.
    """
    
    galaxy_data = list()
    
    for ra, dec in zip(galaxy_ra, galaxy_dec):
        
        
        ned_data = query_closest_ned_source(ra, dec)
        
        
        try:
            sdss_data = query_closest_sdss_source_photoz(ra, dec)
        
        except NoSourcesError:
            sdss_data = pd.DataFrame({'objId': np.nan, 'z': np.nan, 'zErr': np.nan, 'PhotoErrorClass': np.nan},index=[0])
        
        
        try:
            panstarrs_data = query_closest_panstarrs_source(ra, dec)
        
        except NoSourcesError:
            
            panstarrs_columns = ['gApMag', 'gApMagErr', 'rApMag', 'rApMagErr', 'iApMag', 'iApMagErr',
                                 'yApMag', 'yApMagErr', 'zApMag', 'zApMagErr', 
                                 'gKronMag', 'gKronMagErr', 'rKronMag', 'rKronMagErr', 'iKronMag', 'iKronMagErr',
                                 'yKronMag', 'yKronMagErr', 'zKronMag', 'zKronMagErr']
            
            panstarrs_data = pd.DataFrame(columns = panstarrs_columns)
            
            
        galaxy_data.append(pd.concat([ned_data, sdss_data, panstarrs_data], axis=1).reset_index(drop=True))
        
    return pd.concat(galaxy_data).reset_index(drop=True)
    
    