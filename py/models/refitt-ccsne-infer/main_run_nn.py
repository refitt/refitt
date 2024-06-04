""" Main pythin script to run MCMC dynesty simulation with a forced photometry file of a ZTF event as input"""


import csv
import json
import os
import glob
import numpy as np
from dynesty import plotting as dyplot
from tqdm import tqdm
from multiprocessing import Pool
from lc_process import ZTF
from astropy.io import ascii
from astropy.table import Table
import argparse
from interpolate import *
import matplotlib.gridspec as gridspec
import dynesty
from dynesty import NestedSampler
from multiprocessing import Pool
from time import time
import corner
from dynesty.utils import resample_equal
import warnings
import scipy

"Deep Learning Functionalities"
import pickle
import joblib
from joblib import load
from operator import itemgetter
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split


warnings.filterwarnings("ignore")

def parse_args():
    parser= argparse.ArgumentParser()
    parser.add_argument('-obj','--ztfid',default= None, type = str,help='ZTF ID of the object under consideration')
    parser.add_argument('-f','--forced',action='store_true',help='Photometry obtained through difference imaging')
    parser.add_argument('-o', '--output_dir',default = None,help = 'Output Directory where all the output run files are stored')
    parser.add_argument('-days','--n_days',default = None,type = str, help='Number of days you want to include the data of')
    parser.add_argument('-nc','--core',default =None, type = str, help= 'Number of cores needed for the sampler in Pool')
    args =parser.parse_args()
    return args

args = parse_args()

if args.n_days is not None:
    cutoff = float(args.n_days)
elif args.n_days is None:
    cutoff = 200
if args.core is not None:
    num_core = float(args.core)
if args.ztfid is not None:
    ztfobj = str(args.ztfid)
if args.output_dir is not None:
    output = str(args.output_dir)
#if not os.path.exists(ztfobj):
    #os.makedirs(ztfobj)

"""Setting up the dataframes of the ZTF object for dynesty sampling"""

obj = ZTF(ztfobj)
obj.metadata()
#app_g, app_r = obj.pull_from_alerce()
data, upper_limit, available_bands,upper_limit_bands, t_prior = obj.pull_from_alerce()
print(t_prior)


df_cor = {}
for band in available_bands:
    df_cor[band] = obj.all_correct(data[band],band = band,num= cutoff)

#g_cor = obj.all_correct(app_g,band = 'g', num = cutoff)
#r_cor = obj.all_correct(app_r, band = 'r', num = cutoff)

obj.LC_plot(df_cor, upper_limit,available_bands ,upper_limit_bands,num = cutoff,output= output)

"Setting Up the Deep Learning Model"

"Define the neural network architecture"
class NeuralNetwork(nn.Module):
    def __init__(self, input_size, hidden_sizes, output_size):
        super(NeuralNetwork, self).__init__()
        layers = []
        layer_sizes = [input_size] + hidden_sizes + [output_size]
        for i in range(len(layer_sizes) - 1):
            layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
            if i < len(layer_sizes) - 2:
                layers.append(nn.ReLU())
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

"Load all the necessary trained model files. NOTE: The models loaded in here is for scaled data"

model_g = load('./model_g_scaled.joblib')
model_r = load('./model_r_scaled.joblib')
model_i = load('./model_i_scaled.joblib')
with open('./scaler_g_train_scaled.pkl', 'rb') as f:
    scaler_g = pickle.load(f)
with open('./scaler_r_train_scaled.pkl', 'rb') as f:
    scaler_r = pickle.load(f)
with open('./scaler_i_train_scaled.pkl', 'rb') as f:
    scaler_i = pickle.load(f)
with open('./pca_transform_g_train_scaled.pkl', 'rb') as f:
    pca_g = joblib.load(f)
with open('./pca_transform_r_train_scaled.pkl', 'rb') as f:
    pca_r = joblib.load(f)
with open('./pca_transform_i_train_scaled.pkl', 'rb') as f:
    pca_i = joblib.load(f)
def specs(path):
    with open(path, 'rb') as f:
        data = pickle.load(f)
    mean = data.iloc[:,0]
    std = data.iloc[:,1]
    return mean, std
mean_g, std_g = specs('./specs_g_scaled.pkl')
mean_r, std_r = specs('./specs_r_scaled.pkl')
mean_i, std_i = specs('./specs_i_scaled.pkl')

"""Defining Prior And Likelihood Functions For Samping"""

"Setting up prior function and likelihood function for sampling. Now using uniform sampling for all parameters."


def prior_transform(theta):
    zamsp, Ekp, m_lossp, betap, ni_massp,csmr_p, texpp, a_vp= theta 
    zams_min = 10.0
    zams_max = 18.0
    zams_mu, zams_sig = 14, 3.0
    std_zams_low, std_zams_high = (zams_min - zams_mu) / zams_sig, (zams_max - zams_mu) / zams_sig 
    zams = scipy.stats.truncnorm.ppf(zamsp, std_zams_low, std_zams_high, loc=zams_mu, scale=zams_sig)
    
    Ek_min = 0.5
    Ek_max = 5.0
    ek_mu, ek_sig = 1.0, 1.0
    std_ek_low, std_ek_high = (Ek_min - ek_mu) / ek_sig, (Ek_max - ek_mu) / ek_sig 
    Ek = scipy.stats.truncnorm.ppf(Ekp, std_ek_low, std_ek_high, loc=ek_mu, scale=ek_sig)
    
    #m_loss_min = 1
   # m_loss_max = 5
    mloss_m, mloss_s = 4,1.0  # mean and standard deviation
    loss_low, loss_high = 1.0, 5.0  # lower and upper bounds
    low_loss, high_loss = (loss_low - mloss_m) / mloss_s, (loss_high - mloss_m) / mloss_s  # standardize
    m_loss= scipy.stats.truncnorm.ppf(m_lossp, low_loss, high_loss, loc=mloss_m, scale=mloss_s)
    
    
    beta_min = 0.5
    beta_max = 5.0
    beta_mu, beta_sig = 3.00, 0.5
    std_bta_low, std_bta_high = (beta_min - beta_mu) / beta_sig, (beta_max - beta_mu) / beta_sig 
    beta= scipy.stats.truncnorm.ppf(betap, std_bta_low, std_bta_high, loc=beta_mu, scale=beta_sig)
    
    ni_m, ni_s = 0.04, 0.03  # mean and standard deviation
    low, high = 0.001, 0.3  # lower and upper bounds
    low_ni, high_ni = (low - ni_m) / ni_s, (high - ni_m) / ni_s  # standardize
    ni_mass= scipy.stats.truncnorm.ppf(ni_massp, low_ni, high_ni, loc=ni_m, scale=ni_s)
    
    csmr_min = 1
    csmr_max = 10
    
    texp_min = 0.0
    texp_max = t_prior + 5.0
    #t_mu , t_sig = 5,2
    #low_t, high_t = (texp_min - t_mu) / t_sig, (texp_max - t_mu) / t_sig  # standardize
    #texp = scipy.stats.truncnorm.ppf(texpp, low_t, high_t, loc=t_mu, scale=t_sig)
    
    
    av_min = 1e-4
    av_max = 10
    av_mu, av_sig = np.log(0.05),2
    av_low, av_high = (av_min - av_mu)/av_sig, (av_max - av_mu)/av_sig
    av = scipy.stats.truncnorm.ppf(a_vp, av_low, av_high, loc=av_mu, scale=av_sig)
    
    #zams = zamsp*(zams_max-zams_min) + zams_min
    #Ek = Ekp*(Ek_max - Ek_min) + Ek_min
    #m_loss = m_lossp*(m_loss_max - m_loss_min) + m_loss_min
    #m_loss = m_loss_mu + m_loss_sig*ndtri(m_lossp)
    #beta = betap*(beta_max - beta_min) +beta_min
    #ni_mass = ni_massp*(ni_mass_max - ni_mass_min) + ni_mass_min
    #ni_mass = ni_mass_mu + ni_mass_sig*ndtri(ni_massp)
    texp = texpp*(texp_max - texp_min) + texp_min
    csmr = csmr_p*(csmr_max-csmr_min) + csmr_min
    #av = a_vp*(av_max - av_min)+av_min
    
    return (zams, Ek, m_loss, beta, ni_mass, csmr, texp, av)


def loglikelihood_dynesty(theta):
    zams, Ek, m_loss, beta, ni_mass, csmr,texp, a_v = theta 
    mag_list = []
    magerr_list = []
    mag_th = []
    for band in available_bands:
        new_epo, mag, mag_err = epoch_gen(df_cor[band],texplosion = theta[6],host = theta[7])
        mag_theory = NN_interpolate(theta=theta[:6],band = band,new_epo = new_epo,
                                    model_g = model_g,scaler_g=scaler_g, pca_g = pca_g,mean_g=mean_g,std_g=std_g,
                                    model_r=model_r,scaler_r=scaler_r,pca_r=pca_r,mean_r=mean_r,std_r=std_r,
                                    model_i=model_i,scaler_i=scaler_i,pca_i=pca_i,mean_i=mean_i,std_i=std_i
                                   )
        mag_list.extend(mag)
        magerr_list.extend(mag_err)
        mag_th.extend(mag_theory)
    err = (np.array(magerr_list))
    return -0.5 * np.sum((np.array(mag_list) - np.array(mag_th)) ** 2 / err)

"""Initializing Nested Sampling after defining the Prior and the Likelihood Function"""

print('dynesty version: {}'.format(dynesty.__version__))

#nlive = 1024 # number of live points
bound = 'multi'   # use MutliNest algorithm for bounds
ndims = 8      # two parameters
sample = 'unif'   # uniform sampling
tol =  0.1    # the stopping criterion

from dynesty import DynamicNestedSampler

with Pool(120) as pool:
    sampler = DynamicNestedSampler(loglikelihood_dynesty, prior_transform, ndims,
                        bound=bound, sample=sample,pool=pool,
                                queue_size=120)
    sampler.run_nested(print_progress=True)
    
"""Collecting the results from the inference"""

results = sampler.results # get results dictionary from sampler

logZdynesty = results.logz[-1]        # value of logZ
logZerrdynesty = results.logzerr[-1]  # estimate of the statistcal uncertainty on logZ
weights = np.exp(results['logwt'] - results['logz'][-1])
samples_dynesty = resample_equal(results.samples, weights)

print("log(Z) = {} ± {}".format(logZdynesty, logZerrdynesty))
print('Number of posterior samples is {}'.format(len(samples_dynesty)))

"""Saving a couple of ouputs here"""

np.savetxt(output+ '/'+ztfobj+'_samples'+'.txt',samples_dynesty)

fig = corner.corner(samples_dynesty,show_titles=True,labels=['ZAMS','Energy','Mass_Loss','Beta','M_Ni56','CSM_radius','t_exp','A_v'], quantiles=[0.16, 0.5, 0.84])
plt.savefig(output +'/'+ztfobj+'_corner_plot'+'.jpg')

#fig, axes = dyplot.traceplot(res, truths=np.zeros(7),
 #                            show_titles=True, trace_cmap='plasma',
 #                            quantiles=None)
#plt.savefig(output +'/'+ztfobj+'_trace_plot'+'.jpg')


"""Plotting the final model and saving the figure and json files"""
mjd_app, mag_app = obj.make_plots_nn(results,df_cor,upper_limit,available_bands,upper_limit_bands, samples_dynesty, output,model_g,scaler_g,pca_g,mean_g,std_g,scaler_r,model_r,pca_r,mean_r,std_r,scaler_i,model_i,pca_i,mean_i,std_i)
obj.make_json_nn(results,samples_dynesty,output,mjd_app,mag_app,band_list= available_bands)

print("Inference Complete")



