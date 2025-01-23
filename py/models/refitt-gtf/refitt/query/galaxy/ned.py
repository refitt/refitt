# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 19:27:41 2023

@author: blgnm
"""
from astroquery.ned import Ned
from astropy import units as u, coordinates
import pandas as pd
import astropy
from refitt.query.galaxy.galaxy_exceptions import NoSourcesError

def query_ned(galaxy_ra: float, galaxy_dec: float, query_radius: astropy.units.core.Unit=0.5 * u.arcmin) -> pd.DataFrame:
    """
    Queries the NASA Extragalactic Database (NED) for all sources within a specified radius

    Parameters
    ----------
    galaxy_ra : float
        Right ascension of galaxy in degrees.
    galaxy_dec : float
        Declination of galaxy in degrees.
    query_radius : astropy.units.core.Unit, optional
        Radius (using astropy.units) around the galaxy location to query. The default is 0.5 arcminutes.

    Returns
    -------
    query_results : pd.DataFrame
        Data frame containing all NED sources within a specified radius.

    """
    
    galaxy_coordinates = coordinates.SkyCoord(ra= galaxy_ra, dec= galaxy_dec,
                              unit=(u.deg, u.deg), frame='icrs')
    
    query_results = Ned.query_region(galaxy_coordinates, radius=query_radius, equinox='J2000.0').to_pandas()
    
    if query_results.empty == True:
        raise NoSourcesError(f'No sources found within {query_radius} radius')
    
    return query_results

def query_closest_ned_source(galaxy_ra: float, galaxy_dec: float, query_radius: astropy.units.core.Unit=0.5 * u.arcmin) -> pd.DataFrame:
    """
    Queries NED for the closest source within a specified radius

    Parameters
    ----------
    galaxy_ra : float
        Right ascension of galaxy in degrees.
    galaxy_dec : float
        Declination of galaxy in degrees.
    query_radius : astropy.units.core.Unit, optional
        Radius (using astropy.units) around the galaxy location to query. The default is 0.5 arcminutes.

    Returns
    -------
    query_results : pd.DataFrame
        Data frame containing the closest NED source within a specified radius.

    """
    
    query_results = query_ned(galaxy_ra, galaxy_dec, query_radius)
    
    return query_results[query_results['Separation'] == query_results['Separation'].min()].iloc[:1,:].reset_index(drop=True)