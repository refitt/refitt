# -*- coding: utf-8 -*-
"""
Created on Sat Jun 17 01:57:34 2023

@author: blgnm
"""
import pandas as pd
import numpy as np
import os
import re
from astropy.coordinates import SkyCoord
from astropy import units as u
from delight.delight import Delight
from refitt.query.galaxy.panstarrs import get_PS1_Pic

def determine_missing_files(ra: list[float], dec: list[float], host_image_directory: str) -> pd.DataFrame:
    """
    Determines which Panstarrs images are missing to avoid repeat downloads.

    Parameters
    ----------
    ra : list[float]
        Right Ascension of source.
    dec : list[float]
        Declination of source.
    host_image_directory : str
        Path to where the fits folder containing all panstarrs images is.

    Returns
    -------
    needed_images : pd.DataFrame
        Data frame containing all the locations that a panstarrs image is needed.

    """
    
    files = os.listdir(host_image_directory + '/fits')
    filters=list()
    downloaded_ra=list()
    downloaded_dec=list()
    matchedfiles=list()
    for f in files:
        if re.match('stack_r_ra(.*?)_dec(.*)_arcsec120.*fits', f):
            flt = 'r'
            ra1, dec1 = re.findall('stack_r_ra(.*?)_dec(.*)_arcsec120.*fits', f)[0]
            filters.append(flt)
            downloaded_ra.append(float(ra1))
            downloaded_dec.append(float(dec1))
            matchedfiles.append(f)
            
    dfpanstamps = pd.DataFrame({"filename": matchedfiles, "filters": filters, "panstamps_ra": downloaded_ra, "panstamps_dec": downloaded_dec})
    
    #Coordinates of new sample
    sn_coords = SkyCoord(ra, dec, unit=(u.deg, u.deg))

    #Coordinates of downloaded files
    panstamps_coords = SkyCoord(dfpanstamps.panstamps_ra.to_numpy(), dfpanstamps.panstamps_dec.to_numpy(), unit=(u.deg, u.deg))

    # find xmatches between requested SNe and available panstamp files
    idx, d2d, d3d = sn_coords.match_to_catalog_sky(panstamps_coords)
    
    sn_locations = pd.DataFrame({'ra':ra, 'dec': dec})
    sn_locations["dist"] = np.array([float(dist / u.arcsec) for dist in d2d])
    sn_locations["filename"] = dfpanstamps.filename.to_numpy()[idx]
    sn_locations.loc[sn_locations.dist > 0.1, "filename"] = ""

    needed_images = sn_locations.loc[sn_locations.filename==""].reset_index(drop=True)
    
    return needed_images

def get_needed_images(needed_images: pd.DataFrame, host_image_directory: str) -> None:
    """
    Queries any missing images from Panstarrs.

    Parameters
    ----------
    needed_images : pd.DataFrame
        Data frame containing all the locations that a panstarrs image is needed.
    host_image_directory : str
        Path to where the fits folder containing all panstarrs images is.

    Returns
    -------
    None

    """
    
    for i in range(len(needed_images)):
        
        #Retrieves cutout image
        a=get_PS1_Pic(needed_images.ra[i], needed_images.dec[i], 480, 'r')
        
        #Saves image in expected format
        a.writeto(host_image_directory + f'/fits/stack_r_ra{needed_images.ra[i]}_dec{needed_images.dec[i]}_arcsec120_{a.header["skycell"]}.fits', overwrite=True)



def get_host_location(ra: list[float], dec: list[float], ztf_ids: list[str], host_image_directory: str) -> pd.DataFrame:
    """
    Gets the most likely host galaxy location for a list of supernovae.

    Parameters
    ----------
    ra : list[float]
        Right Ascension of sources.
    dec : list[float]
        Declination of sources.
    ztf_ids : list[str]
        unique ZTF identifiers.
    host_image_directory : str
        Path to where the fits folder containing all panstarrs images is.

    Returns
    -------
    host_data : pd.DataFrame
        Data frame containing the most likely host galaxy locations of the provided sources.

    """
    
    dclient = Delight(host_image_directory, np.array(ztf_ids), np.array(ra), np.array(dec))
    dclient.download()
    #Gets WCS information
    dclient.get_pix_coords()
    nlevels = 5
    domask = False
    doobject = True
    doplot = False
    dclient.compute_multiresolution(nlevels, domask, doobject, doplot)
    dclient.load_model()
    dclient.preprocess()
    #Predicts location of host galaxy

    dclient.predict()
	
    
    #Estimates size of host galaxy using source extractor
    for oid in dclient.df.index:
    
        dclient.get_hostsize(oid, doplot=False)

    #Saves host data
    #dclient.save()
    
    host_data = dclient.df[['ra', 'dec','dist', 'ra_delight', 'dec_delight',
                                       'ra_sex', 'dec_sex', 'hostsize', 'hostsep', 'mindistsize']]

    host_data = host_data.rename(columns = {'ra_delight': 'host_ra', 'dec_delight': 'host_dec',
                                  'ra_sex': 'ra_source_extractor', 'dec_sex': 'dec_source_extractor'})
    
    host_data['ZTF_ID'] = list(host_data.index)
    
    return host_data.reset_index(drop=True)


def host_galaxy_association(ra: list[float], dec: list[float], ztf_ids: list[str], host_image_directory: str) -> pd.DataFrame:
    """
    Downloads any missing panstarrs images and gets the most likely host galaxy location for a list of supernovae.

    Parameters
    ----------
    ra : list[float]
        Right Ascension of sources.
    dec : list[float]
        Declination of sources.
    ztf_ids : list[str]
        unique ZTF identifiers.
    host_image_directory : str
        Path to where the fits folder containing all panstarrs images is.

    Returns
    -------
    pd.DataFrame
        Data frame containing the most likely host galaxy locations of the provided sources.

    """
    
    needed_images = determine_missing_files(ra, dec, host_image_directory)
    
    get_needed_images(needed_images, host_image_directory)
    
    return get_host_location(ra, dec, ztf_ids, host_image_directory)
