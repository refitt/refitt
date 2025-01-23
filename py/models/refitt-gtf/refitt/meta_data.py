# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 23:36:11 2023

@author: blgnm
"""
import numpy as np
import pandas as pd
from astropy.table import QTable
import astropy
from dataclasses import dataclass

def redshift_mask(best_redshift: np.ndarray, other_redshift: np.ndarray):
    """
    creates mask to determine which values of best redshift to fill
    """
    return np.where((np.isnan(other_redshift) == False) & (np.isnan(best_redshift) == True))

def get_best_redshift(photoz: np.ndarray, photoz_err: np.ndarray, 
                  hostgal_specz: np.ndarray, hostgal_specz_err: np.ndarray, 
                  sn_z: np.ndarray, sn_z_err: np.ndarray):
    """
    Using all available redshifts it returns an array containing the best ones available for each object as well as their errors.
    When no redshift is available, a default of 0.05 +/- 0.1 is assumed.
    """
    
    best_redshift = np.array([np.nan]*len(photoz))
    best_redshift_err = np.array([np.nan]*len(photoz))
    
    for redshift, redshift_err in zip([sn_z, hostgal_specz, photoz], [sn_z_err, hostgal_specz_err, photoz_err]):
        
        mask = redshift_mask(best_redshift, redshift)
        
        best_redshift_err[mask] = redshift_err[mask] 
        best_redshift[mask] = redshift[mask] 
    
    
    #Fill in remaining missing values with a reasonable guess
    missing_mask = np.where(np.isnan(best_redshift) == True)
    
    best_redshift_err[missing_mask] = 0.1
    best_redshift[missing_mask] = 0.05
    
    return best_redshift, best_redshift_err

def format_meta_data(object_id: np.ndarray[str], ra: np.ndarray[float], dec: np.ndarray[float], 
                     photoz: np.ndarray[float], photoz_err: np.ndarray[float], hostgal_specz: np.ndarray[float],
                     hostgal_specz_err: np.ndarray[float], sn_z: np.ndarray[float], 
                     sn_z_err: np.ndarray[float], transient_type: np.ndarray[str]) -> astropy.table.QTable:
    """
    Puts the meta data into the format expected by Parsnip.
    """

    best_redshift, best_redshift_err = get_best_redshift(photoz, photoz_err, hostgal_specz,
                                                         hostgal_specz_err, sn_z, sn_z_err)

    #We set these to nan in order to utilize the custom error bars on all redshift within parsnip on all events.
    #What we end up calling "hostgal_photoz" is actually the best redshift and associated error available.
    redshift = [np.nan]*len(best_redshift)
    hostgal_specz = [np.nan]*len(best_redshift)
    
    meta_data = [object_id, ra, dec, transient_type, redshift, hostgal_specz, best_redshift, best_redshift_err]
    meta_data_column_names = ('object_id', 'ra', 'dec', 'type', 'redshift', 'hostgal_specz', 
                              'hostgal_photoz', 'hostgal_photoz_err')
    
    return QTable(meta_data, names=meta_data_column_names, dtype=[str, float, float, str, float, float, float, float])


@dataclass
class MetaData:
    """
    Data class that handles the storing of all supernova meta data.
    """
    
    #Supernova meta data
    object_id: np.ndarray[str]
    type: np.ndarray[str]
    ra: np.ndarray[float]
    dec: np.ndarray[float]
    
    #Host Association
    host_ra: np.ndarray[float]
    host_dec: np.ndarray[float]
    host_size: np.ndarray[float]
    host_separation: np.ndarray[float]
    
    #Redshifts
    hostgal_photoz: np.ndarray[float]
    hostgal_photoz_err: np.ndarray[float]
    hostgal_specz: np.ndarray[float]
    supernova_redshift: np.ndarray[float]
    
    #panstarrs host photometry
    gKronMag: np.ndarray[float]
    rKronMag: np.ndarray[float]
    iKronMag: np.ndarray[float]
    yKronMag: np.ndarray[float]
    zKronMag: np.ndarray[float]
    
    gKronMagErr: np.ndarray[float]
    rKronMagErr: np.ndarray[float]
    iKronMagErr: np.ndarray[float]
    yKronMagErr: np.ndarray[float]
    zKronMagErr: np.ndarray[float]

    def to_pandas(self) -> pd.DataFrame:
        return pd.DataFrame(self.__dict__)
