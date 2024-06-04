import numpy as np
from scipy.spatial import distance
import csv
import matplotlib.pyplot as plt
import json
import os
import glob
import pandas as pd
"Deep Learning Functionalities"
import pickle
import joblib
from joblib import load
from operator import itemgetter
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split


def epoch_gen(df,texplosion,host):
    dif_mjd = df.mjd[0] - texplosion
    new_epo = df.mjd - dif_mjd
    df['epoch'] = new_epo
    df_filtered = df[df['epoch'] <= 168.00]
    df_filtered.Ab_obs_mag = df_filtered.Ab_obs_mag - host
    return df_filtered.epoch, df_filtered.Ab_obs_mag, df_filtered.mag_error


def all_arrays(theta,points,delta):
    arr = []
    dist = []
    for i in range(0,len(points)):
        w = weight(theta,points[i],delta)
        eu = distance.euclidean(theta, points[i])
        dist.append(eu)
        arr.append(w)
    return arr,dist


def weight(theta, theta_i, delta):
    #print(theta_i)
    w_abs = np.absolute(np.subtract(theta,theta_i))
    w = np.add(w_abs,delta)
    w_final = 1/np.prod(w)
    #print(w_final)
    return w_final

def interpol_LC_master_scaled(theta,band,new_epo,names,new_points,delta,fine_epoch_g,fine_epoch_r):
    point_prime = np.array(theta[:5])
    mag_th = []
    model_arr = pd.DataFrame()
    model_arr['Model'] = names
    array,distance = np.array(all_arrays(point_prime,new_points,delta))
    model_arr['weights'] = array
    model_arr['distance'] = distance
    total = np.sum(model_arr.weights)
    model_arr['fractions'] = model_arr['weights']/total
    for i in range(0,len(new_epo)):
        epoch = round(new_epo[i],2)
        index = int(epoch/0.01)
        if((band == 'g') or (band == 'zg')):
            values = fine_epoch_g[index]
        elif((band == 'r') or (band == 'zr')):
            values = fine_epoch_r[index]
        inter_mag = model_arr.fractions.ravel().dot(values.ravel())
        mag_th.append(inter_mag)
    return mag_th

def get_params(x):
    median = []
    m_l = []
    m_u= []
    for i in range(7):
        mcmc = np.percentile(x[:, i], [16, 50, 84])
        q = np.diff(mcmc)
        median.append(mcmc[1])
        m_l.append(q[0])
        m_u.append(q[1])
    return median, m_l, m_u

def new_epoch_gen(X,theta,band):
    texp = theta[5]
    obs_epo = None
    appar_epoch = None
    if (len(X) < 2):
        obs_epo = X[band]['mjd'] - (X[band]['mjd'][0] - texp)
        appar_epoch = np.linspace(X[band]['mjd'][0]-texp,(X[band]['mjd'][0]-texp+150),100)
    else:
        offset = abs(X['g']['mjd'][0] - X['r']['mjd'][0])
        if band == 'r':
            if X['g']['mjd'][0] < X['r']['mjd'][0]:
                obs_epo = X['r']['mjd'] - (X['r']['mjd'][0] - texp) + offset
                appar_epoch = np.linspace((X['r']['mjd'][0]-texp-offset),(X['r']['mjd'][0]-texp+offset+150),100)
            else:
                obs_epo = X['r']['mjd'] - (X['r']['mjd'][0] - texp)
                appar_epoch = np.linspace(X['r']['mjd'][0]-texp,(X['r']['mjd'][0]-texp+150),100)
        elif band == 'g':
            if X['g']['mjd'][0] > X['r']['mjd'][0]:
                obs_epo = X['g']['mjd'] - (X['g']['mjd'][0] - texp) + offset
                appar_epoch = np.linspace(X['g']['mjd'][0]-texp-offset,X['g']['mjd'][0]-texp+ offset +150,100)
            else:
                obs_epo = X['g']['mjd'] - (X['g']['mjd'][0] - texp)
                appar_epoch = np.linspace(X['g']['mjd'][0]-texp,X['g']['mjd'][0]-texp+150,100)
    return obs_epo, appar_epoch


"Deep Learning Model Necessary Functions"

def get_params_nn(x):
    median = []
    m_l = []
    m_u= []
    for i in range(8):
        mcmc = np.percentile(x[:, i], [16, 50, 84])
        q = np.diff(mcmc)
        median.append(mcmc[1])
        m_l.append(q[0])
        m_u.append(q[1])
    return median, m_l, m_u

def new_epoch_gen_nn(X,theta,band):
    texp = theta[6]
    obs_epo = None
    appar_epoch = None
    if (len(X) < 2):
        obs_epo = X[band]['mjd'] - (X[band]['mjd'][0] - texp)
        appar_epoch = np.linspace(X[band]['mjd'][0]-texp,(X[band]['mjd'][0]-texp+150),100)
    else:
        offset = abs(X['g']['mjd'][0] - X['r']['mjd'][0])
        if band == 'r':
            if X['g']['mjd'][0] < X['r']['mjd'][0]:
                obs_epo = X['r']['mjd'] - (X['r']['mjd'][0] - texp) + offset
                appar_epoch = np.linspace((X['r']['mjd'][0]-texp-offset),(X['r']['mjd'][0]-texp+offset+150),100)
            else:
                obs_epo = X['r']['mjd'] - (X['r']['mjd'][0] - texp)
                appar_epoch = np.linspace(X['r']['mjd'][0]-texp,(X['r']['mjd'][0]-texp+150),100)
        elif band == 'g':
            if X['g']['mjd'][0] > X['r']['mjd'][0]:
                obs_epo = X['g']['mjd'] - (X['g']['mjd'][0] - texp) + offset
                appar_epoch = np.linspace(X['g']['mjd'][0]-texp-offset,X['g']['mjd'][0]-texp+ offset +150,100)
            else:
                obs_epo = X['g']['mjd'] - (X['g']['mjd'][0] - texp)
                appar_epoch = np.linspace(X['g']['mjd'][0]-texp,X['g']['mjd'][0]-texp+150,100)
    return obs_epo, appar_epoch


def band_interpolate(theta,model,scaler,pca,mean,std):
    model.eval()
    model_specs_tensor = torch.tensor([theta])
    # Scale the model_specs tensor
    scaled_specs = scaler.transform(model_specs_tensor)
    #print(scaled_specs)
    # Perform model inference
    with torch.no_grad():
        reconstructed = pca.inverse_transform(model(torch.Tensor(scaled_specs))[0].detach().numpy())
    interpolated = (reconstructed *std) + mean
    #print(interpolated)
    return interpolated
    
def NN_interpolate(theta, band, new_epo, model_g,  scaler_g,pca_g,mean_g, std_g,
                   model_r, scaler_r, pca_r, mean_r, std_r,
                   model_i, scaler_i, pca_i, mean_i, std_i
                  ):
    indices = [int(round(num, 2) / 0.01) for num in new_epo]

    if (band == 'g') or (band == 'zg'):
        result = band_interpolate(theta, model_g, scaler_g, pca_g, mean_g, std_g)
    elif (band == 'r') or (band == 'zr'):
        result = band_interpolate(theta, model_r, scaler_r, pca_r, mean_r, std_r)
    elif (band == 'i') or (band == 'zi'):
        result = band_interpolate(theta, model_i, scaler_i, pca_i, mean_r, std_i)
    else:
        raise ValueError("Invalid band specified")

    values = np.atleast_1d(itemgetter(*indices)(result)).tolist()
    return values




    