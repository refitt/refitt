# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 21:26:05 2023

@author: blgnm
"""
import parsnip
from argparse import ArgumentParser
import pandas as pd
from astropy.table import Table
import astropy
import warnings
warnings.filterwarnings('ignore')

def update_classes(training_data: astropy.table.Table) -> astropy.table.Table:
    """
    Removes classes from training data that we don't want and consolidates the names into the 5 main classes of Type Ia, II, Ibc, SLSN, and IIn.

    Parameters
    ----------
    training_data : astropy.Table
        Training data from the parsnip model predictions.

    Returns
    -------
    astropy.Table
        Astropy table containing the reformatted training data.

    """
    training_data = training_data.to_pandas()
    training_data = training_data[training_data['type']!='NA']
    
    remove = ['Unknown','FELT','TDE','SN','LBV','Other','LRN', 'unknown', 'SN I', 'TDE-H-He']
    training_data = training_data[training_data['type'].isin(remove)==False].reset_index(drop=True)
    training_data['type']=training_data['type'].replace(['SNIa-norm','SNIc','SNIb','SNIIb','SNIc-BL','SNIbn','SNIa-CSM','SLSN-II','SNIa-91bg-like',
                                      'SNIb-pec','SLSN-I','SNIa-SC','SNIa-91T-like','SNIax', 'SN Ia', 'SN II', 'SN Ia-91T',
                                      'SN Ic', 'SN Ib', 'SN IIb', 'SN IIP', 'SN Ic-BL', 'SN Ia-91bg','SN Ia-pec', 'SN Ibn',
                                      'SN Ib/c', 'SN Iax', 'SN II-pec', 'SN Ia-CSM', 'SN Ib-pec', 'SN Ia-SC', 'SN Icn', 'SN Ic-pec',
                                      'SN Ia-91bg-like', 'SN Ia-91T-like', 'SN Iax[02cx-like]', 'SN Ib-Ca-rich', 'SN IIL', 'SN IIn-pec', 'SN Ic-Ca-rich', 'SN Ia-Ca-rich'],
                                     ['SNIa','SNIbc','SNIbc','SNII','SNIbc','SNIbc','SNIa','SLSN','SNIa','SNIbc','SLSN','SNIa',
                                     'SNIa','SNIa', 'SNIa', 'SNII', 'SNIa', 'SNIbc', 'SNIbc', 'SNII', 'SNII', 'SNIbc', 'SNIa',
                                     'SNIa','SNIbc','SNIbc','SNIa','SNII','SNIa','SNIbc','SNIa','SNIbc','SNIbc', 'SNIa', 'SNIa', 'SNIa', 'SNIbc',
                                     'SNII', 'SNIIn', 'SNIbc', 'SNIa'])
    
    training_data.loc[training_data['type']=='SN IIn','type']='SNIIn'
    
    return Table.from_pandas(training_data.reset_index(drop=True))

def main(training_data_paths: list[str], parsnip_model_path: str, n_augments: int=10,
         classifier_save_path: str='./classifier') -> None:
    
    dataset = parsnip.load_datasets(training_data_paths, require_redshift=False)
    
    model = parsnip.load_model(parsnip_model_path)
    
    processed_dataset = model.preprocess(dataset)
    
    training_data = model.predict_dataset_augmented(processed_dataset, n_augments).copy()
    
    training_data = update_classes(training_data)
    
    #original_mask = ~training_data['augmented']
    classifier = parsnip.Classifier()
    classifier.train(training_data)
    
    classifier.write(classifier_save_path)
    

if __name__ == '__main__':
    
    parser = ArgumentParser()
    
    parser.add_argument('-training_data_paths', type=str, help="List of paths to the training data for the model")
    parser.add_argument('-parsnip_model_path', type=str, help="Path to parsnip model.")
    parser.add_argument('--classifier_save_path', type=str, default='./classifier', help="Path to save classifier to.")
    parser.add_argument('--n_augments', type=int, default=10, help="Number of times to augment classifier training data.")

    args = parser.parse_args()
    
    main(args.training_data_paths.split(','), args.parsnip_model_path, args.n_augments, args.classifier_save_path)
    
    



    