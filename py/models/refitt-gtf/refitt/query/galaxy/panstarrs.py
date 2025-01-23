# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 19:27:01 2023

@author: blgnm
"""
import pandas as pd
import numpy as np
import requests
import astropy
from astropy import units as u, coordinates
from astropy.io import ascii, fits
from astropy.table import Table
from refitt.query.galaxy.galaxy_exceptions import NoSourcesError

def remove_bad_panstarrs_sources(panstarrs_data: pd.DataFrame) -> pd.DataFrame:
    """
    Removes Panstarrs sources that have bad photometry according to their flags.

    Parameters
    ----------
    panstarrs_data : pd.DataFrame
        Data frame containing panstarrs photometry.

    Returns
    -------
    pd.DataFrame
        Filtered Panstarrs photometry data frame.

    """
    
    panstarrs_data = panstarrs_data[panstarrs_data['primaryDetection']==1]
    panstarrs_data = panstarrs_data[panstarrs_data['QualityFlag'] != 128]
    panstarrs_data = panstarrs_data[(panstarrs_data['gPSFMag'] != -999)]
    panstarrs_data = panstarrs_data[(panstarrs_data['rPSFMag'] != -999)]
    panstarrs_data = panstarrs_data[(panstarrs_data['iPSFMag'] != -999)]
    
    return panstarrs_data.reset_index(drop=True)


def checklegal(table,release):
    """Checks if this combination of table and release is acceptable
    
    Raises a VelueError exception if there is problem
    """
    
    releaselist = ("dr1", "dr2")
    if release not in ("dr1","dr2"):
        raise ValueError("Bad value for release (must be one of {})".format(', '.join(releaselist)))
    if release=="dr1":
        tablelist = ("mean", "stack")
    else:
        tablelist = ("mean", "stack", "detection")
    if table not in tablelist:
        raise ValueError("Bad value for table (for {} must be one of {})".format(release, ", ".join(tablelist)))


def ps1metadata(table: str="mean",release: str="dr1",
           baseurl: str="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs") -> astropy.table.table.Table:
    """Return metadata for the specified catalog and table
    
    Parameters
    ----------
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    baseurl: base URL for the request
    
    Returns an astropy table with columns name, type, description
    """
    
    checklegal(table,release)
    url = "{baseurl}/{release}/{table}/metadata".format(**locals())
    r = requests.get(url)
    r.raise_for_status()
    v = r.json()
    # convert to astropy table
    tab = Table(rows=[(x['name'],x['type'],x['description']) for x in v],
               names=('name','type','description'))
    return tab

def ps1search(table: str="mean",release: str="dr1",format: str="csv",columns: list[str]=None,
           baseurl: str="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs", verbose: bool=False,
           **kw):
    """Do a general search of the PS1 catalog (possibly without ra/dec/radius)
    
    Parameters
    ----------
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2).  Note this is required!
    """
    
    data = kw.copy()
    if not data:
        raise ValueError("You must specify some parameters for search")
    checklegal(table,release)
    if format not in ("csv","votable","json"):
        raise ValueError("Bad value for format")
    url = "{baseurl}/{release}/{table}.{format}".format(**locals())
    if columns:
        # check that column values are legal
        # create a dictionary to speed this up
        dcols = {}
        for col in ps1metadata(table,release)['name']:
            dcols[col.lower()] = 1
        badcols = []
        for col in columns:
            if col.lower().strip() not in dcols:
                badcols.append(col)
        if badcols:
            raise ValueError('Some columns not found in table: {}'.format(', '.join(badcols)))
        # two different ways to specify a list of column values in the API
        # data['columns'] = columns
        data['columns'] = '[{}]'.format(','.join(columns))

# either get or post works
#    r = requests.post(url, data=data)
    r = requests.get(url, params=data)

    if verbose:
        print(r.url)
    r.raise_for_status()
    if format == "json":
        return r.json()
    else:
        return r.text

def ps1cone(ra: float,dec: float,radius: float, table: str="mean",release: str="dr1",format: str="csv",columns: list[str]=None,
           baseurl: str="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs", verbose: bool=False,
           **kw):
    """Do a cone search of the PS1 catalog
    
    Parameters
    ----------
    ra (float): (degrees) J2000 Right Ascension
    dec (float): (degrees) J2000 Declination
    radius (float): (degrees) Search radius (<= 0.5 degrees)
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2)
    """
    
    data = kw.copy()
    
    data['ra'] = ra
    data['dec'] = dec
    data['radius'] = radius
    
    return ps1search(table=table,release=release,format=format,columns=columns,
                    baseurl=baseurl, verbose=verbose, **data)



def query_panstarrs(galaxy_ra: float, galaxy_dec: float, arcminute_query_radius: float=30) -> pd.DataFrame:
    """
    Queries Panstarrs for all sources within a specificed arcminute radius.

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
        Data frame containing all Panstarrs sources within the specified radius.

    """
    
    
    #Columns for photometry, meta data, and various data flags
    columns = ['objID','primaryDetection','bestDetection','QualityFlag','raMean','decMean',
               'objName','gPSFMag', 'gPSFMagErr', 'gApMag', 'gApMagErr', 'gKronMag', 'gKronMagErr', 'gpsfMajorFWHM', 
               'gpsfMinorFWHM', 'gmomentXX', 'gmomentXY', 'gmomentYY', 'gmomentR1', 'gmomentRH', 'gPSFFlux', 
               'gPSFFluxErr', 'gApFlux', 'gApFluxErr', 'gApRadius', 'gKronFlux', 'gKronFluxErr', 'gKronRad', 
               'gExtNSigma', 'rPSFMag', 'rPSFMagErr', 'rApMag', 'rApMagErr', 'rKronMag', 'rKronMagErr', 'rpsfMajorFWHM', 
               'rpsfMinorFWHM', 'rmomentXX', 'rmomentXY', 'rmomentYY', 'rmomentR1', 'rmomentRH', 'rPSFFlux', 
               'rPSFFluxErr', 'rApFlux', 'rApFluxErr', 'rApRadius', 'rKronFlux', 'rKronFluxErr', 'rKronRad', 
               'rExtNSigma', 'iPSFMag', 'iPSFMagErr', 'iApMag', 'iApMagErr', 'iKronMag', 'iKronMagErr', 'ipsfMajorFWHM', 
               'ipsfMinorFWHM', 'imomentXX', 'imomentXY', 'imomentYY', 'imomentR1', 'imomentRH', 'iPSFFlux', 'iPSFFluxErr', 
               'iApFlux', 'iApFluxErr', 'iApRadius', 'iKronFlux', 'iKronFluxErr', 'iKronRad', 'iExtNSigma', 'zPSFMag', 
               'zPSFMagErr', 'zApMag', 'zApMagErr', 'zKronMag', 'zKronMagErr', 'zpsfMajorFWHM', 'zpsfMinorFWHM', 
               'zmomentXX', 'zmomentXY', 'zmomentYY', 'zmomentR1', 'zmomentRH', 'zPSFFlux', 'zPSFFluxErr', 'zApFlux', 
               'zApFluxErr', 'zApRadius', 'zKronFlux', 'zKronFluxErr', 'zKronRad', 'zExtNSigma', 'yPSFMag', 
               'yPSFMagErr', 'yApMag', 'yApMagErr', 'yKronMag', 'yKronMagErr', 'ypsfMajorFWHM', 'ypsfMinorFWHM', 
               'ymomentXX', 'ymomentXY', 'ymomentYY', 'ymomentR1', 'ymomentRH', 'yPSFFlux', 'yPSFFluxErr', 'yApFlux', 
               'yApFluxErr', 'yApRadius', 'yKronFlux', 'yKronFluxErr', 'yKronRad', 'yExtNSigma']
    
    columns = [x.strip() for x in columns]
    columns = [x for x in columns if x and not x.startswith('#')]
    
    query_results = ps1cone(galaxy_ra, galaxy_dec, arcminute_query_radius/3600, release='dr1', columns=columns, table="stack")
    
    if query_results == '':
        raise NoSourcesError("Likely outside of Panstarrs survey footprint.")
    
    panstarrs_data = ascii.read(query_results).to_pandas()
    
    return remove_bad_panstarrs_sources(panstarrs_data)
    

def query_closest_panstarrs_source(galaxy_ra: float, galaxy_dec: float, arcminute_query_radius: float=30) -> pd.DataFrame:
    """
    Queries Panstarrs for the closest source within a specificed arcminute radius.

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
    TYPE
        Data frame containing the closest Panstarrs source within the specified radius.

    """
    
    panstarrs_data = query_panstarrs(galaxy_ra, galaxy_dec, arcminute_query_radius)
    
    galaxy_coordinates = coordinates.SkyCoord(ra= galaxy_ra, dec= galaxy_dec,
                              unit=(u.deg, u.deg), frame='icrs')
    
    panstarrs_source_coordinates = coordinates.SkyCoord(ra= panstarrs_data.raMean.values, dec= panstarrs_data.decMean.values,
                                                        unit=(u.deg, u.deg), frame='icrs')
    
    source_separation = galaxy_coordinates.separation(panstarrs_source_coordinates)*u.arcsec

    panstarrs_data['separation'] = source_separation
    
    photometry_columns = ['gApMag', 'gApMagErr', 'rApMag', 'rApMagErr', 'iApMag', 'iApMagErr',
                          'yApMag', 'yApMagErr', 'zApMag', 'zApMagErr', 
                          'gKronMag', 'gKronMagErr', 'rKronMag', 'rKronMagErr', 'iKronMag', 'iKronMagErr',
                          'yKronMag', 'yKronMagErr', 'zKronMag', 'zKronMagErr']
    
    return panstarrs_data.sort_values(by='separation').iloc[:1,:].reset_index(drop=True)[photometry_columns]

#Panstarrs image queries

def get_PS1_Pic(ra: float, dec: float, rad: float, band: str, safe: bool=False) -> np.ndarray:
    """
    

    Parameters
    ----------
    ra : Float
        Right ascension of object.
    dec : Float
        Declanation of object.
    rad : Float
        Radius in arcseconds from object to search.
    band : str
        Filter image should be in.
    safe : Bool, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    Numpy Array
        Image of radius rad at the specified location from the panstarrs survey.

    """
    fitsurl = geturl(ra, dec, size=rad, filters="{}".format(band), format="fits")
    fh = fits.open(fitsurl[0])
    return fh[0]

def geturl(ra: float, dec: float, size: int=240, output_size: int=None, filters: str="grizy", format: str="jpg", 
           color: bool=False, type: str='stack') -> str:

    """Get URL for images in the table
    ra, dec = position in degrees
    size = extracted image size in pixels (0.25 arcsec/pixel)
    output_size = output (display) image size in pixels (default = size).
                  output_size has no effect for fits format images.
    filters = string with filters to include
    format = data format (options are "jpg", "png" or "fits")
    color = if True, creates a color image (only for jpg or png format).
            Default is return a list of URLs for single-filter grayscale images.
    Returns a string with the URL
    """

    if color and format == "fits":
        raise ValueError("color images are available only for jpg or png formats")
    if format not in ("jpg","png","fits"):
        raise ValueError("format must be one of jpg, png, fits")
    table = getimages(ra,dec,size=size,filters=filters, type=type)
    url = ("https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
           "ra={ra}&dec={dec}&size={size}&format={format}").format(**locals())
    if output_size:
        url = url + "&output_size={}".format(output_size)
    # sort filters from red to blue
    flist = ["yzirg".find(x) for x in table['filter']]
    table = table[np.argsort(flist)]
    if color:
        if len(table) > 3:
            # pick 3 filters
            table = table[[0,len(table)//2,len(table)-1]]
        for i, param in enumerate(["red","green","blue"]):
            url = url + "&{}={}".format(param,table['filename'][i])
    else:
        urlbase = url + "&red="
        url = []
        for filename in table['filename']:
            url.append(urlbase+filename)
    return url

def getimages(ra: float,dec: float,size: int=240,filters: str="grizy", type: str='stack') -> astropy.table.table.Table:

    """Query ps1filenames.py service to get a list of images
    ra, dec = position in degrees
    size = image size in pixels (0.25 arcsec/pixel)
    filters = string with filters to include
    Returns a table with the results
    """

    service = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
    url = ("{service}?ra={ra}&dec={dec}&size={size}&format=fits"
           "&filters={filters}&type={type}").format(**locals())
    table = Table.read(url, format='ascii')
    return table

