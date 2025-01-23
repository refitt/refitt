# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 01:22:49 2023

@author: blgnm
"""

from refitt.query.antares import query_antares_light_curves
from refitt.query.galaxy.cross_match_galaxy import cross_match_galaxies
from refitt.host_galaxy_association import host_galaxy_association
from refitt.meta_data import MetaData
from refitt.light_curve import LightCurve
from refitt.query.tns import query_entire_tns_catalog, cross_match_with_tns
from refitt.parsnip_model import ParsnipModel, evaluate_model
from refitt.plot import compare_multiple_lc
import pandas as pd
import warnings
from argparse import ArgumentParser
warnings.filterwarnings('ignore')

def supernova_meta_data_to_dict(ztf_id: list[str], ra: list[float], dec: list[float],host_locations: pd.DataFrame, 
                                galaxy_data: pd.DataFrame, tns: pd.DataFrame) -> dict:
    """
    Converts the various data in the main() function into a dictionary that can be easily fed into the MetaData class.
    """
    
    sorted_ids = pd.DataFrame({'ZTF_ID': ztf_id, 'ra': ra, 'dec': dec}).sort_values(by='ZTF_ID')
    
    return {'object_id': sorted_ids.ZTF_ID.values, 'ra': sorted_ids.ra.values, 'dec': sorted_ids.dec.values, 
            'host_ra': host_locations.host_ra.values,
            'host_dec': host_locations.host_dec.values, 'host_size': host_locations.hostsize.values,
            'host_separation': host_locations.hostsep.values, 'hostgal_photoz': galaxy_data.z.values,
            'hostgal_photoz_err': galaxy_data.zErr.values, 'hostgal_specz': galaxy_data.Redshift.values,
            'supernova_redshift': tns.redshift.values, 'type': tns.classification.values, 
            'gKronMag': galaxy_data.gKronMag.values, 'rKronMag': galaxy_data.rKronMag.values, 
            'iKronMag': galaxy_data.iKronMag.values, 'yKronMag': galaxy_data.yKronMag.values, 
            'zKronMag': galaxy_data.zKronMag.values, 'gKronMagErr': galaxy_data.gKronMagErr.values, 
            'rKronMagErr': galaxy_data.rKronMagErr.values, 'iKronMagErr': galaxy_data.iKronMagErr.values, 
            'yKronMagErr': galaxy_data.yKronMagErr.values, 'zKronMagErr': galaxy_data.zKronMagErr.values}

def main(ztf_id: str, model_output_path: str, obs_output_path: str, meta_output_path: str, plot_output_dir: str, 
         host_image_directory: str='../../host'):
    
    lcs, ra, dec = query_antares_light_curves(ztf_id)
    
    host_locations = host_galaxy_association(ra, dec, ztf_id, host_image_directory).sort_values(by='ZTF_ID')
    
    galaxy_data = cross_match_galaxies(host_locations.host_ra, host_locations.host_dec)
    
    #Only use if you don't have catalog file or if you need to update it.
    #query_entire_tns_catalog(file_name='tns_data.zip')
    
    tns_catalog = pd.read_csv('tns_data.zip', skiprows=1)
    
    tns = cross_match_with_tns(tns_catalog, pd.DataFrame({'ZTF_ID': ztf_id, 'ra': ra, 'dec': dec})).sort_values(by='ZTF_ID')
    
    meta_data = MetaData(**supernova_meta_data_to_dict(ztf_id, ra, dec, host_locations, galaxy_data, tns))
    
    light_curve = LightCurve(lcs.mjd.values, lcs.magnitude.values, lcs.error.values, 
                    lcs.band.values, lcs.object_id.values)
    
    model = ParsnipModel(model_path='./bts_ps1_bg.pt', classifier_path='./classifier')
    
    predictions, parsnip_lc, classifications = evaluate_model(model, meta_data, light_curve)
    
    meta_data = pd.concat([meta_data.to_pandas(), classifications.sort_values(by='object_id').drop(columns=['object_id']),
                          predictions.sort_values(by='object_id').drop(columns=['object_id', 'type'])], axis=1)
    
    compare_multiple_lc(lcs, parsnip_lc, classification = meta_data[['object_id', 'SNIa', 'SNII', 'SNIIn', 'SNIbc', 'SLSN']],
                        tns_classification=tns, reduced_chi_squared=meta_data[['object_id', 'model_chisq', 'model_dof']], redshifts=meta_data[['object_id','hostgal_photoz', 'hostgal_photoz_err', 'hostgal_specz', 'supernova_redshift']],
                        file_name_dir=plot_output_dir)
    
    parsnip_lc.to_csv(model_output_path)
    lcs.to_csv(obs_output_path)
    meta_data.to_csv(meta_output_path)
    
if __name__ == '__main__':
    
    parser = ArgumentParser()
    parser.add_argument('--ztf_id', type=str, default=None, help="IDs of ZTF events to query for.")
    parser.add_argument('--text_file_path', type=str, default=None, help="CSV file of ZTF_IDs to use instead of --ztf_id")
    
    parser.add_argument('--model_output_path', type=str, default='./model_lc.csv', help="Parsnip model light curves output path.")
    parser.add_argument('--obs_output_path', type=str, default='./obs_lc.csv', help="Observed light curves output path.")
    parser.add_argument('--meta_output_path', type=str, default='./lc_meta.csv', help="Meta data output path.")
    parser.add_argument('--plot_output_dir', type=str, default='./plot/', help="Directory to save plots in.")
    parser.add_argument('--host_image_directory', type=str, default='../../host', help="Directory to save host images in.")
    
    
    args = parser.parse_args()
    
    if (args.ztf_id is None) & (args.text_file_path is None):
        raise SyntaxError("Both --ztf_id and --text_file_path can't be None.")
    
    if (args.ztf_id is not None) & (args.text_file_path is not None):
        raise SyntaxError("Both --ztf_id and --text_file_path can't both have values.")
        
    if args.text_file_path is not None:
        ztf_id = pd.read_csv(args.text_file_path).ZTF_ID.values.tolist()
    
    if args.ztf_id is not None:
        ztf_id = args.ztf_id.split(',')
    
    
    main(ztf_id, args.model_output_path, args.obs_output_path, args.meta_output_path, args.plot_output_dir, args.host_image_directory)
    
