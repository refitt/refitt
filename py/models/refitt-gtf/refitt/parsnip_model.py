# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 01:07:37 2023

@author: blgnm
"""

import parsnip
import lcdata
import pandas as pd
import numpy as np
import torch
import astropy
from refitt.model import Model
from refitt.light_curve import LightCurve
from refitt.meta_data import MetaData
from astropy.table import QTable

class ParsnipModel(Model):
    """
    Class for easily interacting with the parsnip model from the package parsnip
    """
    
    def __init__(self, model_path: str, classifier_path: str):
        
        self.model_path = model_path
        self.classifier_path = classifier_path
        
    def load_model(self) -> None:
        self.model = parsnip.load_model(self.model_path)
        
    def load_classifier(self) -> None:
        classifier = parsnip.Classifier()
        
        self.classifier = classifier.load(self.classifier_path)
    
    def classify(self, predictions) -> pd.DataFrame:
        return self.classifier.classify(predictions).to_pandas()

    def predict_light_curve(self, dataset: lcdata.dataset) -> pd.DataFrame:
        return get_parsnip_model_lc(dataset, self.model)
    
    def predict(self, dataset: lcdata.dataset) -> astropy.table.Table:
        return self.model.predict(dataset.light_curves)
    
    def format_lc_and_meta(self, meta_data: MetaData, light_curve: LightCurve) -> lcdata.dataset:
        
        parsnip_meta_data = meta_data_to_parsnip_format(meta_data)
        
        return lcdata.from_observations(parsnip_meta_data, light_curve.parsnip_format)
    
    def preprocess_dataset(self, dataset: lcdata.dataset) -> lcdata.dataset:
        return self.model.preprocess(dataset)

def get_parsnip_model_lc(dataset: lcdata.Dataset, parsnip_model: parsnip.ParsnipModel) -> pd.DataFrame:
    """
    Predicts the full transient light curve using the parsnip model.

    Parameters
    ----------
    dataset : lcdata.Dataset
        parsnip dataset to use for prediction.
    parsnip_model : parsnip.ParsnipModel
        Trained parsnip model.

    Returns
    -------
    pd.DataFrame
        Data frame containing the parsnip model light curves.

    """
    lcs = list()
    for i in range(len(dataset.light_curves)):
        torch.cuda.empty_cache()
        time, flux, model = parsnip_model.predict_light_curve(dataset.light_curves[i], sample=True, count=100,sampling=1,
                                                             pad = 100)
    
        percentile_offset = (100 - 68) / 2.
        mag = 27.5 - 2.5*np.log10(flux)
        mag_median = np.median(mag, axis=0)
    
        mag_max = np.percentile(mag, percentile_offset,
                                 axis=0)
    
        mag_min = np.percentile(mag,
                                 100 - percentile_offset, axis=0)
    
    
        #band=['ztfg', 'ps1::g', 'ps1::r', 'ztfr', 'ps1::i', 'ps1::z']
        band = ['ztfg', 'ps1::g', 'ps1::r', 'ztfr', 'ps1::i', 'ztfi', 'ps1::z']
        parsnip_lc = pd.concat([pd.DataFrame({'magnitude':mag_median[i,:], 'band': band[i], 'upper_bound': mag_max[i,:],
                                             'lower_bound': mag_min[i, :], 'mjd': time}) for i in range(mag_median.shape[0])]).reset_index(drop=True)
    
        parsnip_lc['ZTF_ID'] = dataset.meta[i]['object_id']
        
        parsnip_lc['upper_bound'] = parsnip_lc['magnitude'] - parsnip_lc['upper_bound']
        parsnip_lc['lower_bound'] = parsnip_lc['lower_bound'] - parsnip_lc['magnitude']
        
        parsnip_lc['error'] = (parsnip_lc['upper_bound'] + parsnip_lc['lower_bound'])/2
        
        lcs.append(parsnip_lc)
        
    return pd.concat(lcs).reset_index(drop=True)


def classify_light_curves(parsnip_predictions: astropy.table.Table, classifier: parsnip.Classifier) -> pd.DataFrame:
    """
    Classifies light curves based on the parsnip model predictions

    Parameters
    ----------
    parsnip_predictions : astropy.table.Table
        Predictions generated from parsnip model.
    classifier : parsnip.Classifier
        Classifier trained on parsnip model parameters.

    Returns
    -------
    pd.DataFrame
        Data frame containing the classifications.

    """
    return classifier.classify(parsnip_predictions).to_pandas()
    
    
def redshift_mask(best_redshift: np.ndarray, other_redshift: np.ndarray):
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

def meta_data_to_parsnip_format(meta_data: MetaData) -> astropy.table.Table:
    """
    Converts a MetaData object to the format expected by parsnip
    """
    
    default_supernova_redshift_err = np.array([0.01]*len(meta_data.object_id))
    default_hostgal_specz_err = np.array([0.01]*len(meta_data.object_id))
    
    best_redshift, best_redshift_err = get_best_redshift(meta_data.hostgal_photoz, meta_data.hostgal_photoz_err, 
                                                         meta_data.hostgal_specz, default_hostgal_specz_err, 
                                                         meta_data.supernova_redshift, default_supernova_redshift_err)
    
    redshift = np.array([np.nan]*len(best_redshift))
    hostgal_specz = np.array([np.nan]*len(best_redshift))
    
    parsnip_meta_data = [meta_data.object_id, meta_data.ra, meta_data.dec, meta_data.type, redshift, hostgal_specz, best_redshift,
                         best_redshift_err]
    parsnip_meta_data_column_names = ('object_id', 'ra', 'dec', 'type', 'redshift', 'hostgal_specz', 
                              'hostgal_photoz', 'hostgal_photoz_err')
    
    return QTable(parsnip_meta_data, names=parsnip_meta_data_column_names, dtype=[str, float, float, str, float, float, float, float])
    

def evaluate_model(model: Model, meta_data: MetaData, light_curves: LightCurve) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Predicts parsnip parameters, classifications, and model light curves for a set of supernovae.
    """
        
    model.load_model()
    model.load_classifier()
    
    dataset = model.format_lc_and_meta(meta_data, light_curves)
    
    dataset = model.preprocess_dataset(dataset)
    
    predictions = model.predict(dataset)
    parsnip_lc = model.predict_light_curve(dataset)
        
    classifications = model.classify(predictions)
    
    return predictions.to_pandas(), parsnip_lc, classifications
