# -*- coding: utf-8 -*-
"""
Created on Thu Jun 15 20:44:11 2023

@author: blgnm
"""

import pandas as pd
import numpy as np

class score:
    
    def __init__(self, obs_lc, model_lc):
        
        self.obs_lc = obs_lc
        self.model_lc = model_lc
        self.interpolated_model_lc = None
        self.residuals = None
        
    
    def interpolate_model(self):
        """
        Interpolates model values at the observed values for easy comparison.
        """
        
        interpolated_data = list()
        
        for band in self.obs_lc.band.unique():
            
            obs = self.obs_lc.loc[self.obs_lc['band'] == band]
            model = self.model_lc.loc[self.model_lc['band']==band]
            
            interpolated_mag = np.interp(obs.mjd, model.mjd, model.magnitude)
        
            interpolated_data.append(pd.DataFrame({'magnitude': interpolated_mag, 
                                                   'mjd': obs.mjd.values, 
                                                   'band': [band]*len(interpolated_mag)}))
        
        
        self.interpolated_model_lc = pd.concat(interpolated_data).reset_index(drop=True)
        
    def calculate_abs_residuals(self):
        
        resid = list()
        
        for band in self.obs_lc.band.unique():
            
            model = self.interpolated_model_lc
            model = model.loc[model['band'] == band].sort_values(by='mjd').reset_index(drop=True)
            
            obs = self.obs_lc
            obs = obs.loc[obs['band'] == band].sort_values(by='mjd').reset_index(drop=True)
            
            diff = np.abs(model.magnitude.values - obs.magnitude.values)
            
            resid.extend(diff.tolist())
            
        self.residuals = resid
            
    
    def refitt_score(self, alpha=1):
        
        a = np.sum(self.residuals)/len(self.residuals)
        
        model = self.model_lc
        obs = self.obs_lc
        
        errors = model[(model['mjd'] > (obs['mjd'].min() - 20)) & (model['mjd'] < (obs['mjd'].min() + 80))]['error'].values
        
        b = alpha*np.sum(errors)
        
        self.score = a + b
    
            
    