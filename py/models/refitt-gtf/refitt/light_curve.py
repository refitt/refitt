# -*- coding: utf-8 -*-
"""
Created on Sat Jun 17 01:54:33 2023

@author: blgnm
"""
from refitt.plot import plot_light_curve
from astropy.table import QTable
import astropy
import numpy as np

def mag_to_flux(magnitude: list[float]) -> list[float]:
    """
    Converts magnitude values to flux using a zeropoint of 27.5 (we normalize all fluxes to have that zeropoint in the parsnip model)

    """
    return [10**((mag-27.5)/-2.5) for mag in magnitude]

def mag_err_to_flux_err(magnitude_error: list[float], flux: list[float]) -> list[float]:
    """
    Converts magnitude errors to flux errors
    """
    return [abs(flux[i]*magnitude_error[i]*(np.log(10.)/2.5)) for i in range(len(magnitude_error))]

class LightCurve:
    """
    Class that handles storing light curve data
    """
    
    def __init__(self, time: np.ndarray[float], magnitude: np.ndarray[float], 
                 magnitude_errors: np.ndarray[float], band: np.ndarray[str],
                 object_id: list[str]):
        
        self.time = time
        self.magnitude = magnitude
        self.band = band
        self.magnitude_errors = magnitude_errors
        self.object_id = object_id
        
    @property
    def flux(self) -> list[float]:
        return mag_to_flux(self.magnitude)
    
    @property
    def flux_err(self) -> list[float]:
        return mag_err_to_flux_err(self.magnitude_errors, self.flux) 
    
    @property
    def days_since_trigger(self) -> np.ndarray[float]:
        return self.time - np.min(self.time)
    
    @property
    def parsnip_format(self) -> astropy.table.QTable:
        return QTable([self.time, self.flux, self.flux_err, self.band, self.object_id],
                      names = ('time', 'flux', 'fluxerr', 'band', 'object_id'))
    
    def plot_light_curve(self):
        return plot_light_curve(self.time, self.magnitude, self.magnitude_errors, self.bands)
    
    