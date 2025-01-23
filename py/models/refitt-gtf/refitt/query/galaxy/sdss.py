# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 19:27:31 2023

@author: blgnm
"""
from astroquery.sdss import SDSS
import pandas as pd
from refitt.query.galaxy.galaxy_exceptions import NoSourcesError


def query_sdss(galaxy_ra: float, galaxy_dec: float, arcminute_query_radius: float=0.5) -> pd.DataFrame:
    """
    Queries the Sloan Digital Sky Survey (SDSS) for all sources within a specified radius

    Parameters
    ----------
    galaxy_ra : float
        Right ascension of galaxy in degrees.
    galaxy_dec : float
        Declination of galaxy in degrees.
    arcminute_query_radius : float, optional
        SDSS query radius in arcminutes. The default is 0.5.

    Raises
    ------
    NoSourcesError
        Raises error if no sources are found within the specified radius.

    Returns
    -------
    sdss_query : pd.DataFrame
        Data frame of all SDSS sources within the specified radius.

    """
    sdss_query = f'SELECT TOP 100 G.objID, GN.distance FROM Galaxy as G JOIN dbo.fGetNearbyObjEq({galaxy_ra},{galaxy_dec}, {arcminute_query_radius}) AS GN ON G.objID = GN.objID ORDER BY distance'
    
    sdss_query = SDSS.query_sql(sdss_query)
    
    if sdss_query is None:
        raise NoSourcesError(f'No SDSS sources within {arcminute_query_radius} arcminute radius')
        
    return sdss_query

def query_sdss_photoz(sdss_id: int) -> pd.DataFrame:
    """
    Queries SDSS for the photometric redshift information of a given SDSS source ID.

    Parameters
    ----------
    sdss_id : int
        Unique SDSS source identifier.

    Returns
    -------
    pd.DataFrame
        Data frame containing the photometric redshift information of the given SDSS source ID.

    """
    
    photometric_redshift_query = f'SELECT objId,z,zErr,PhotoErrorClass FROM Photoz WHERE objID = {sdss_id}'
    
    return SDSS.query_sql(photometric_redshift_query).to_pandas()


def query_closest_sdss_source_photoz(galaxy_ra: float, galaxy_dec: float, arcminute_query_radius: float=0.5) -> pd.DataFrame:
    """
    Queries SDSS for the closest source's photometric redshift (photoz) in a specified radius

    Parameters
    ----------
    galaxy_ra : float
        Right ascension of galaxy in degrees.
    galaxy_dec : float
        Declination of galaxy in degrees.
    arcminute_query_radius : float, optional
        SDSS query radius in arcminutes. The default is 0.5.

    Returns
    -------
    pd.DataFrame
        Data frame containing the closest source's photoz in SDSS within the specified radius.

    """
    
    closest_sdss_source_id = query_sdss(galaxy_ra, galaxy_dec, arcminute_query_radius)[0]['objID']
    
    return query_sdss_photoz(closest_sdss_source_id)