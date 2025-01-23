# -*- coding: utf-8 -*-
"""
Created on Sat Jun 17 01:44:40 2023

@author: blgnm
"""
from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from astropy.wcs import WCS
import pandas as pd

#Matplotlib parameters
rcParams['font.family'] = 'serif'
rcParams['mathtext.default'] = 'regular'
plt.rcParams.update({'font.size':20})

#Default colors for different bandpasses
band_plot_colors = {'ztfr': 'red', 'ztfg': 'green', 'ztfi': 'purple', 
                    'ps1::g': 'darkgreen', 'ps1::r': 'darkred', 'ps1::i': 'orange', 'ps1::z':'indigo'}

def plot_light_curve(times: np.ndarray[float], magnitudes: np.ndarray[float], 
                     magnitude_errors: np.ndarray[float], bandpasses: np.ndarray[str], 
                     band_plot_colors: dict = band_plot_colors, title: str = None, ax=None) -> plt.Axes:
    """
    Plots light curve using matplotlib

    Parameters
    ----------
    times : np.ndarray[float]
        Light curve times to plot on x-axis.
    magnitudes : np.ndarray[float]
        Light curve magnitudes to plot on y-axis.
    magnitude_errors : np.ndarray[float]
        Light curve magnitude errors.
    bandpasses : np.ndarray[str]
        bandpass that each magnitude uses.
    band_plot_colors : dict, optional
        dictionary setting the color for each unique bandpass. The default is band_plot_colors.
    title : str, optional
        Plot title. The default is None.
    ax : plt.Axes, optional
        Pass through a premade axis to plot on. The default is None.

    Returns
    -------
    ax : plt.Axes
        Matplotlib axes that contains the plot.

    """
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, dpi=250, figsize=(10,10), facecolor='white')
    
    unique_bands = np.unique(bandpasses)
    
    for band in unique_bands:
        
        band_mask = np.where(bandpasses == band)
        
        ax.errorbar(times[band_mask], magnitudes[band_mask], yerr=magnitude_errors[band_mask],
                     mec = 'black', color=band_plot_colors[band], fmt='o')
    
    ax.set_xlabel('MJD')
    ax.set_ylabel('Magnitude')
    ax.minorticks_on()
    ax.tick_params(which='both', direction='in', top=True, right=True)
    
    if title is not None:
        ax.set_title(title)

    
    if ax is None:
        ax.invert_yaxis()
        fig.tight_layout()
    
    return ax


def plot_parsnip_light_curve(times: np.ndarray[float], magnitudes: np.ndarray[float], 
                     magnitude_errors: np.ndarray[float], bandpasses: np.ndarray[str], 
                     band_plot_colors: dict = band_plot_colors, title: str = None, ax=None) -> plt.Axes:
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, dpi=250, figsize=(10,10), facecolor='white')
    
    unique_bands = np.unique(bandpasses)
    
    for band in unique_bands:
        
        band_mask = np.where(bandpasses == band)
        
        ax.plot(times[band_mask], magnitudes[band_mask], color=band_plot_colors[band], label=band)
        ax.fill_between(times[band_mask], (magnitudes[band_mask] - magnitude_errors[band_mask]), (magnitudes[band_mask] + magnitude_errors[band_mask]),
                        alpha=0.2, color=band_plot_colors[band])
        
    
    ax.set_xlabel('MJD')
    ax.set_ylabel('Magnitude')
    ax.minorticks_on()
    ax.tick_params(which='both', direction='in', top=True, right=True)
    
    if title is not None:
        ax.set_title(title)
        
    if ax is None:
        ax.invert_yaxis()
        fig.tight_layout()
       
        
    
    return ax

def compare_obs_to_model(obs_lc: pd.DataFrame, model_lc: pd.DataFrame, file_name: str='comparison.png', title=None,
                         reduced_chi_squared: float=np.nan, tns_classification: str='None', p_ia: float=np.nan,
                         p_ii: float=np.nan, p_iin: float=np.nan, p_ibc: float=np.nan, p_slsn: float=np.nan, tns_redshift: float=np.nan, host_spec_z: float=np.nan, photoz: float=np.nan, photoz_err: float=np.nan) -> None:
    """
    Plots the standard comparison plot between the parsnip model and the observed data.

    Parameters
    ----------
    obs_lc : pd.DataFrame
        Data frame containing the observed light curve.
    model_lc : pd.DataFrame
        Data frame containing the fitted model light curve.
    file_name : str, optional
        Name to save the plot as. The default is 'comparison.png'.
    title : TYPE, optional
        Title of the plot. The default is None.
    reduced_chi_squared : float, optional
        Model reduced chi squared to put on plot. The default is np.nan.
    tns_classification : str, optional
        Transient Name server classification to display. The default is 'None'.
    p_type: float, optional
        probability to display for each class (Ia, II, Ibc, IIn, SLSN).    
    
    Returns
    -------
    None
       
    """
    
    fig, ax = plt.subplots(1,1,dpi=250, figsize=(11,8))
    
    #masking the values instead of changing axis limits allows us to still utilize auto axis scaling in the other axis
    #model_mask = np.where((model_lc.magnitude.values < 22))
    plot_parsnip_light_curve(model_lc.mjd.values, model_lc.magnitude.values, model_lc.error.values, 
                             model_lc.band.values, ax=ax)
    
    plot_light_curve(obs_lc.mjd.values, obs_lc.magnitude.values, obs_lc.error.values, obs_lc.band.values, ax=ax)
    ax.set_xlim(obs_lc.mjd.min() - 50, np.min([obs_lc.mjd.max() + 150, model_lc.mjd.max()])) 
    #ax.set_ylim(np.min(model_lc.magnitude.values) - 0.5, 22)
    
    if title is not None:
        ax.set_title(title)
    
    annotation_string = r'$\tilde{\chi}^2: $' + str(round(reduced_chi_squared, 3))
    annotation_string += '\n'
    annotation_string += f'TNS: {tns_classification}'
    annotation_string += '\n'
    annotation_string += '\n'
    annotation_string += 'Classification:'
    annotation_string += '\n'
    annotation_string += f'P(Ia)={round(p_ia, 3)}'
    annotation_string += '\n'
    annotation_string += f'P(II)={round(p_ii, 3)}'
    annotation_string += '\n'
    annotation_string += f'P(IIn)={round(p_iin, 3)}'
    annotation_string += '\n'
    annotation_string += f'P(Ibc)={round(p_ibc, 3)}'
    annotation_string += '\n'
    annotation_string += f'P(SLSN)={round(p_slsn, 3)}'
    annotation_string += '\n'
    annotation_string += '\n'
    annotation_string += 'Redshift:'
    annotation_string += '\n'
    annotation_string += f'TNS: {tns_redshift}'
    annotation_string += '\n'
    annotation_string += 'Host$_{spec_z}$: '+f'{host_spec_z}'
    annotation_string += '\n'
    annotation_string += 'Host$_{photo_z}$: '+f'{photoz}' + r' $\pm$ ' +  f'{photoz_err}'
  
    ax.annotate(annotation_string, (1.01, .34), (1.01, .34), xycoords='axes fraction')
    ax.legend(fontsize=15)
    ax.invert_yaxis()
    
    fig.tight_layout()
    plt.savefig(file_name)
    fig.clear()
    plt.close(fig)
    
    
def compare_multiple_lc(obs_lc: pd.DataFrame, model_lc: pd.DataFrame, classification: pd.DataFrame, file_name_dir: str='./plot/',
                        reduced_chi_squared: pd.DataFrame=np.nan, tns_classification: str='None', redshifts=None):
    """
    Uses the compare_obs_to_model function on a list of supernovae.
    """
    
    for ztf_id in obs_lc['object_id'].unique():
        
        prob = classification[classification['object_id']==ztf_id]
        chi = reduced_chi_squared[reduced_chi_squared['object_id'] == ztf_id]
        chi = chi.model_chisq.values[0]/chi.model_dof.values[0]
        redshift = redshifts[redshifts['object_id']==ztf_id]
        
        compare_obs_to_model(obs_lc[obs_lc['object_id']==ztf_id], model_lc[model_lc['ZTF_ID']==ztf_id], file_name = file_name_dir + ztf_id + '.png',
                             title=ztf_id, reduced_chi_squared=chi, tns_classification=tns_classification[tns_classification['ZTF_ID']==ztf_id].classification.values[0], 
                             p_ia=prob.SNIa.values[0], p_ii=prob.SNII.values[0], p_iin=prob.SNIIn.values[0], p_ibc=prob.SNIbc.values[0], p_slsn=prob.SLSN.values[0], tns_redshift=round(redshift.supernova_redshift.values[0],3),host_spec_z=round(redshift.hostgal_specz.values[0][0],3), photoz=round(redshift.hostgal_photoz.values[0][0], 3), photoz_err=round(redshift.hostgal_photoz_err.values[0][0],3))

    

def plot_galaxy(hdu: fits.PrimaryHDU, title: str = None, ax: plt.Axes = None) -> plt.Axes:
    """
    Plots fits image using matplotlib

    Parameters
    ----------
    hdu : fits.PrimaryHDU
        Opened fits file.
    title : str, optional
        Plot title. The default is None.
    ax : plt.Axes, optional
        Pass through a premade axis to plot on. The default is None.

    Returns
    -------
    ax : plt.Axes
        Matplotlib axes that contains the plot.

    """
    
    
    wcs = WCS(hdu.header)
    
    if ax is None:
        fig, ax = plt.subplots(dpi=200, figsize=(10,10), subplot_kw=dict(projection=wcs))
        
        ax.set_xlabel('Right Ascension')
        ax.set_ylabel('Declination')
        
    ax.imshow(hdu.data, vmin=-2.e-5, vmax=2.e-4, origin='lower')
    
    if title is not None:
        ax.set_title(title)
    
    if ax is None:
        fig.tight_layout()
    
    return ax
