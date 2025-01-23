# -*- coding: utf-8 -*-
"""
Created on Sun Jun 18 23:19:46 2023

@author: blgnm
"""

import numpy as np
import os
import sys
import parsnip
import time
from argparse import ArgumentParser

def main(training_data_path, output_model_path='./parsnip_model.pt'):
    
    start_time = time.time()

    args = {'model_path':output_model_path, 'dataset_paths':['./data/bg_phot4.h5', './data/bts_phot4.h5', './data/yse_phot6.h5', './data/ps1_phot.h5'],
           'overwrite':False, 'max_epochs':1000, 'split_train_test':False, 'bands':None,
           'device':'cuda','threads':16,'predict_redshift':True,'batch_size':256,'learning_rate':5e-4, 'zeropoint':27.5}

    # Figure out if we have already trained a model at this path.
    model_path = args['model_path']
    if os.path.exists(model_path):
        if args['overwrite']:
            print(f"Model '{model_path}' already exists, overwriting!")
        else:
            print(f"Model '{model_path}' already exists, skipping!")
            sys.exit()

    # dataset = parsnip.load_datasets(
    #     ['./data/ztf2.h5','./data/ps1.h5','./data/YSE.h5','./data/test.h5'],
    #     require_redshift=False,
    # )

    #dataset = parsnip.load_datasets(
    #    ['./data/bg_phot4.h5', './data/bts_phot4.h5', './data/ps1_phot.h5'],
    #    require_redshift=False,
    #)
    
    dataset = parsnip.load_datasets(
        training_data_path,
        require_redshift=False,
    )
    
    # Figure out which bands we want to use for the model. If specific ones were
    # specified on the command line, use those. Otherwise, use all available bands.
    bands = args.pop('bands')
    if bands is None:
        bands = parsnip.get_bands(dataset)
    else:
        bands = bands.split(',')

    model = parsnip.ParsnipModel(
        model_path,
        bands,
        device='cuda',
        threads=args['threads'],
        settings=args,
        ignore_unknown_settings=True
    )

    dataset = model.preprocess(dataset)

    
    if args['split_train_test']:
        train_dataset, test_dataset = parsnip.split_train_test(dataset)
        model.fit(train_dataset, test_dataset=test_dataset,
                  max_epochs=args['max_epochs'])
    else:
        train_dataset = dataset
        model.fit(train_dataset, max_epochs=args['max_epochs'])

    # Save the score to a file for quick comparisons. If we have a small dataset,
    # repeat the dataset several times when calculating the score.
    rounds = int(np.ceil(25000 / len(train_dataset)))

    train_score = model.score(train_dataset, rounds=rounds)
    if args['split_train_test']:
        test_score = model.score(test_dataset, rounds=10 * rounds)
    else:
        test_score = -1.

    end_time = time.time()

    # Time taken in minutes
    elapsed_time = (end_time - start_time) / 60.

    with open('./parsnip_results.log', 'a') as f:
        print(f'{model_path} {model.epoch} {elapsed_time:.2f} {train_score:.4f} '
              f'{test_score:.4f}', file=f)
        
        
if __name__ == '__main__':
    
    parser = ArgumentParser()
    
    parser.add_argument('-training_data_path', type=str, help="Path to model training data.")
    parser.add_argument('--output_model_path', default='./parsnip_model.pt', type=str, help="Path to save output model.")
    args = parser.parse_args()
    
    
    main(args.training_data_path.split(','), args.output_model_path)
    
    
    
    
    
    
    
    
    
    