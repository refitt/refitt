"""A python module to process the light curves from apparant magnitude to absolute magnitude
This also have functions that will correct for extinction for each filter


Created by Bhagya Subrayan
Dated: December 14 2022
"""
import json
import itertools
from astropy import units as u
import math as m
import sfdmap
import extinction
import glob
import sys
from astropy.coordinates import Angle
import pandas as pd
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle
from astropy import units as u
from alerce.core import Alerce
from datetime import datetime
from antares_client.search import get_by_ztf_object_id
import sncosmo
from tns_redshift import redshift
from interpolate import *
from astropy.cosmology import FlatLambdaCDM
from astropy.io import ascii
from astropy.table import Table

class ZTF(object):
    '''Object class for each REFITT Recommended Object, using ZTF ID numbers and the antares database'''
    def __init__(self, locusID):
        self.ZTF_ID = locusID
        self.locus = get_by_ztf_object_id(self.ZTF_ID)
        self.coord_RA = Angle(self.locus.ra*u.degree).to_string(u.hour, sep=':')
        self.coord_DEC = Angle(self.locus.dec*u.degree).to_string(u.deg, alwayssign=True, sep=':')
        self.z = self.redshift()
        self.dmod = self.distmod()
        self.filter = self.pull_from_alerce()[2]
        #self.g = self.pull_from_alerce()[0]
        #self.r = self.pull_from_alerce()[1]
        self.ebv = self.calculate_extinction()[1]
        self.ext = self.calculate_extinction()[0]
        #self.Ar = self.extinction()[1]
        self.datetoday = Time(datetime.utcnow(),scale='utc').mjd
        self.SNclass= redshift(self.ZTF_ID)['TNSclass']

    def redshift(self):
        try:
            return float(redshift(self.ZTF_ID)['redshift'])
        except Exception:
            print('No redshift found in TNS. Inference for this event aborted')
            sys.exit(1)

    def distmod(self):
        cosmo = FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=2.725)
        dmod = cosmo.distmod(self.z)
        return dmod.value
    
    def metadata(self):
        print('Event:',self.ZTF_ID)
        print('Distance Modulus:',self.dmod)
        print('Redshift:', self.z )
        print('RA,Dec :',self.coord_RA + ',' + self.coord_DEC)

    def pull_from_alerce(self):
        """
        Parameters
        ----------
        eventname : str
            ZTF event name.

        Returns
        -------
        data_frames : tuple
            Tuple of Pandas DataFrames containing lightcurve information.
        available_bands : list
            List of available bands ('g', 'r', etc.).
        """

        alerce = Alerce()

        # Query detections and upper limits
        detections = alerce.query_detections(self.ZTF_ID, format="pandas")
        upper_limits = alerce.query_non_detections(self.ZTF_ID, format="pandas")
        first_detection = alerce.query_object(self.ZTF_ID)['firstmjd']
        upper_limits = upper_limits[upper_limits['mjd'] < first_detection]
        if (len(upper_limits) != 0):
            deep_up_mjd = upper_limits[upper_limits['diffmaglim'] == upper_limits['diffmaglim'].max()]['mjd'].values[0]
            t_prior = first_detection - deep_up_mjd
        else:
            print('Warning: No upper limits to constrain the prior. Defaulting to t_prior = 60 days')
            t_prior = 60.0

        # Extract relevant columns and rename 'fid' to band
        detections = detections[['mjd', 'magpsf', 'sigmapsf', 'fid']]
        detections['band'] = detections['fid'].replace({1: 'g', 2: 'r',3:'i'})

        # Determine available bands for detections
        available_bands = np.sort(detections['band'].unique().tolist())

        # Print available bands for detections
        print('Data available in bands:', available_bands)

        # Separate data frames for each band in detections
        data_frames = {}

        for band in available_bands:
            data_frames[band] = detections[detections['band'] == band].reset_index(drop=True)

        # Determine available bands for upper limits
        upper_limit_bands =np.sort(upper_limits['fid'].replace({1: 'g', 2: 'r'}).unique().tolist())
        upper_limits['band'] = upper_limits['fid'].replace({1: 'g', 2: 'r'})

        # Print available bands for upper limits
        print('Upper limits available in bands:', upper_limit_bands)

        # Separate data frames for each band in upper limits
        upper_limit_frames = {}

        for band in upper_limit_bands:
            upper_limit_frames[band] = upper_limits[upper_limits['band'] == band].reset_index(drop=True)

        return data_frames, upper_limit_frames, available_bands,upper_limit_bands, t_prior

    def extinction(self):
        dustmap = sfdmap.SFDMap("./sncosmo/sfddata-master")
        c = SkyCoord(self.coord_RA + self.coord_DEC, unit=(u.hourangle, u.deg))
        ebv = dustmap.ebv(c)
        Ar = 2.751*ebv   #1998 prescription
        Ag = 3.793*ebv
        #Ai = 2.086*ebv
        #Az = 1.479*ebv
        return Ag, Ar, ebv
    
    def calculate_extinction(self):
        # Function to calculate extinction for given celestial coordinates and filter list
        dustmap = sfdmap.SFDMap("/project/amalthea/bsubraya/CCSNe_Inference/sncosmo/sfddata-master/")
        c = SkyCoord(self.coord_RA + self.coord_DEC, unit=(u.hourangle, u.deg))
        ebv = dustmap.ebv(c)

        filters_names = []
        a_lambdas = []

        for filter in self.filter:
            filter_band = sncosmo.get_bandpass('ztf'+filter)
            effective_wavelength = np.array([filter_band.wave_eff])

            filters_names.append(filter)
            a_lambdas.append(extinction.fitzpatrick99(effective_wavelength, ebv * 3.1, 3.1))

        # Create a dictionary
        a_lambda_dict = dict(zip(filters_names, a_lambdas))
        #print(a_lambda_dict)
        return a_lambda_dict, ebv


    def all_correct(self,df,band,num):
        df = df[df.mjd < df.mjd[0] +num].reset_index(drop=True)
        df['Ab_obs_mag'] = df.magpsf -self.dmod - self.ext[band]
        mu, sigma = 0.005,0.001
        s = np.random.normal(mu,sigma,1)
        df['mag_error'] = df.sigmapsf + s
        return df

    def LC_plot(self,data,upper_limit, bands,upper_limit_bands,num,output):
        #plt.figure(figsize = (5,5))
        #up_ext = {'g':self.Ag,'r':self.Ar}
        for band in bands:
            plt.errorbar(data[band].mjd,data[band].Ab_obs_mag, yerr =data[band].mag_error,fmt = 'o',label = band,markeredgecolor = 'k')
            if band in upper_limit_bands:
                plt.plot(upper_limit[band].mjd,upper_limit[band].diffmaglim -self.dmod - self.ext[band],'v', alpha = 0.4)
            else:
                continue
        #plt.errorbar(df2.mjd, df2.Ab_obs_mag, yerr = df2.mag_error,fmt = 'ro',label = 'r')
        plt.gca().invert_yaxis()
        plt.ylim(-13,-19)
        #plt.xlim(df1.mjd[0], df1.mjd[0]+10)
        plt.legend()
        plt.title(self.ZTF_ID + '< ' + str(num) + ' '+'days' )
        plt.ylabel('Absolute Magnitude')
        plt.xlabel('MJD')
        plt.savefig(output+'/'+ self.ZTF_ID+'_abs.png',dpi = 100,bbox_inches = 'tight')
        
    "Making Linear Algebra Interpolation JSON files - 4208 Models Incorporated"

    def make_json(self,results,samples,output, mjd_app,mag_app,band_list):
        ut_mjd = Time(datetime.utcnow(), scale='utc').mjd
        zipped = itertools.zip_longest(*get_params(samples), fillvalue=None)
        err_arr = [0.0]*len(mjd_app[0])
        logZdynesty = results.logz[-1]        
        logZerrdynesty = results.logzerr[-1]  
        outputArray = [list(item) for item in zipped]
        for i in range(0,len(band_list)):
            output_dict = {
            "model_type": "core_collapse_inference",
            "ztf_id": str(self.ZTF_ID),
            "filter": band_list[i],
            "mjd_arr": mjd_app[i],
            "mag_arr": mag_app[i],
            "err_arr" : err_arr,
            "mjd": ut_mjd,
            "parameters" :{
            "zams" : outputArray[0],
            "k_energy" : outputArray[1],
            "mloss_rate":  outputArray[2],
            "beta":  outputArray[3],
            "56Ni" :  outputArray[4],
            "texp" :  outputArray[5],
            "A_v" :  outputArray[6],
            "logZ" : [logZdynesty,logZerrdynesty,logZerrdynesty],
            "Phase" : ut_mjd - mjd_app[i][0]}}
            #print(output_dict)
            with open(output + '/'+self.ZTF_ID+ '_'+ band_list[i].strip('-')[0]+".json", "w") as outfile:
                json.dump(output_dict, outfile)
                
    "Making Neural Network Interpolation JSON files - All Models Incorporated"

    def make_json_nn(self,results,samples,output, mjd_app,mag_app,band_list):
            ut_mjd = Time(datetime.utcnow(), scale='utc').mjd
            zipped = itertools.zip_longest(*get_params(samples), fillvalue=None)
            err_arr = [0.0]*len(mjd_app[0])
            logZdynesty = results.logz[-1]        
            logZerrdynesty = results.logzerr[-1]  
            outputArray = [list(item) for item in zipped]
            for i in range(0,len(band_list)):
                output_dict = {
                "model_type": "core_collapse_inference",
                "ztf_id": str(self.ZTF_ID),
                "filter": band_list[i],
                "mjd_arr": mjd_app[i],
                "mag_arr": mag_app[i],
                "err_arr" : err_arr,
                "mjd": ut_mjd,
                "parameters" :{
                "zams" : outputArray[0],
                "k_energy" : outputArray[1],
                "mloss_rate":  outputArray[2],
                "beta":  outputArray[3],
                "56Ni" :  outputArray[4],
                "csm_radius": outputArray[5],
                "texp" :  outputArray[6],
                "A_v" :  outputArray[7],
                "logZ" : [logZdynesty,logZerrdynesty,logZerrdynesty],
                "Phase" : ut_mjd - mjd_app[i][0]}}
                #print(output_dict)
                with open(output + '/'+self.ZTF_ID+ '_'+ band_list[i].strip('-')[0]+"_nn.json", "w") as outfile:
                    json.dump(output_dict, outfile)


    def make_plots(self,results,df_cor,upper_limit,available_bands,upper_limit_bands, samples, output_dir,names,new_points,delta,fine_epoch_g,fine_epoch_r):
        mjd_app = []
        mag_app = []
        plt.rcParams["font.family"] = "serif"
        plt.rc('axes', linewidth = 2)
        plt.rcParams.update({'font.size': 24})
        inds = np.random.randint(len(samples), size=50)
        fine_epo = np.linspace(0,150,100)
        fig3 = plt.figure(figsize=(10,10))
        fig4 = plt.figure(figsize=(10,10))
        median, m_l, m_u = get_params(samples)
        import matplotlib.gridspec as gridspec
        plt.rcParams['xtick.labelsize'] = 20
        plt.rcParams['ytick.labelsize'] = 20
        col = {'g':'#7BC950','r':'#B93327'}
        col_bands = {'g':'#24991E', 'r':'r'}
        up_ext = {'g':self.Ag,'r':self.Ar}
        ax = fig3.add_subplot(111)
        ax1 = fig4.add_subplot(111)
        ext={'g':(median[6]/3.1)*3.303,'r':(median[6]/3.1)*2.285}

        """Making labels for parameters here"""

        new_labels =['ZAMS\,(M {_{\odot}})',r' { {E_{k}}\,( {10^{51}} erg)}',
        ' {-log{_{10}\,\dot{M}}\,(M {_{\odot}\,yr^{-1}}})',
        r'{\beta}',
        '^{56}Ni\,(M_{\odot})',
       ' {t_{exp}\,(day)}',r'{ {A_{V}} (mag)}']
        data = []
        for i in range(7):
            mcmc = np.percentile(samples[:, i], [16, 50, 84])
            q = np.diff(mcmc)
            txt = r"$\rm{{{3}}} = {0:.2f}_{{-{1:.2f}}}^{{{2:.2f}}}$"
            txt_new = txt.format(mcmc[1], q[0], q[1], new_labels[i])
            data.append(txt_new)
            textstr = '\n'.join(data)
        "Adding logZ to the plots"
        logZdynesty = results.logz[-1]        
        logZerrdynesty = results.logzerr[-1]
        logz_txt = txt.format(logZdynesty,logZerrdynesty,logZerrdynesty,'logZ')
        textstr = textstr + '\n'+logz_txt

        for band in available_bands:
            mag_i = []
            mag_new = interpol_LC_master_scaled(median,new_epo = fine_epo,band = band,names = names,new_points = new_points,delta = delta,fine_epoch_g =fine_epoch_g,fine_epoch_r = fine_epoch_r)
            obs_new, appar_epoch = new_epoch_gen(df_cor,median,band= band)
            mag_i.append(list(mag_new + self.dmod+ext[band]+up_ext[band]))
            for ind in inds:
                sample = samples[ind]
                mag_th = interpol_LC_master_scaled(sample,new_epo = fine_epo,band = band,names = names,new_points = new_points,delta = delta,fine_epoch_g =fine_epoch_g,fine_epoch_r = fine_epoch_r)
                app_mag_th = mag_th + self.dmod +ext[band]+up_ext[band]
                mag_i.append(list(app_mag_th))
                ax.plot(fine_epo,mag_th,c = col[band],ls = '--',linewidth = 0.3)#label=theta)
                ax1.plot(appar_epoch,app_mag_th,c = col[band],ls = '--',linewidth = 0.3)#appar_epoch
            mag_app.append(mag_i)
            mjd_app.append(list(appar_epoch))
            ax1.set_ylim(15.0,25)
            ax.set_title(self.ZTF_ID,fontsize = 20)
            ax1.set_title(self.ZTF_ID, fontsize = 20)
            ax1.set_xlim(min(appar_epoch) - 20, max(appar_epoch) +5)
            ax.set_xlim(-10,150)
            ax.set_ylim(-21.0,-10.0)
            ax.set_xlabel('Days from Explosion',fontsize =20)
            ax.set_ylabel('Absolute Magnitude',fontsize = 20)
            ax1.set_xlabel('Modified Julian Date (MJD)',fontsize =20)
            ax1.set_ylabel('Apparent Magnitude',fontsize = 20)
            ax.plot(fine_epo,mag_new,c = col[band],ls = '--',linewidth = 3.0)
            ax1.plot(appar_epoch,mag_new + self.dmod +ext[band]+up_ext[band] ,c = col[band],ls = '--',linewidth = 3.0)#appar_epoch
            ax1.errorbar(df_cor[band].mjd,df_cor[band].magpsf,c = col_bands[band], fmt ='o',ms = '10',yerr = df_cor[band].sigmapsf,label = band + '-ztf',elinewidth=1,markeredgecolor = 'k')
            ax.errorbar(obs_new,df_cor[band].Ab_obs_mag-ext[band],c = col_bands[band], fmt ='o',ms = '10',yerr = df_cor[band].mag_error,label = band+ '-ztf',elinewidth=1,markeredgecolor = 'k')
            ax.legend(prop={'size': 20},loc = 'upper right',bbox_to_anchor=(1.0, 0.98), frameon = False)
            ax1.legend(prop={'size': 20},loc = 'upper right',bbox_to_anchor=(1.0, 0.98), frameon = False)
            ax1.text(0.25, 0.05, textstr, transform=ax1.transAxes, fontsize=15,verticalalignment='bottom',usetex = True,linespacing=2.0)
            ax.text(0.25, 0.05, textstr, transform=ax.transAxes, fontsize=15, verticalalignment='bottom',usetex = True,linespacing=2.0)
            ax.minorticks_on()
            ax.tick_params(axis='both',right=True, top=True, which='both')
            ax.tick_params(axis='both',which='major',direction='in',size=20,labelsize='20',width=3)
            ax.tick_params(axis='both',which='minor',direction='in',size=10,width=3)
            ax.locator_params(axis='x', nbins=5)
            ax.locator_params(axis='y', nbins=5)
            ax1.minorticks_on()
            ax1.tick_params(axis='both',right=True, top=True, which='both')
            ax1.tick_params(axis='both',which='major',direction='in',size=20,labelsize='20',width=3)
            ax1.tick_params(axis='both',which='minor',direction='in',size=10,width=3)
            ax1.locator_params(axis='x', nbins=5)
            ax1.locator_params(axis='y', nbins=5)
            if band in upper_limit_bands:
                ax1.plot(upper_limit[band].mjd,upper_limit[band].diffmaglim,'v',c = col_bands[band],alpha = 0.4)
                ax.plot(upper_limit[band].mjd - df_cor[band].mjd[0]+median[5], upper_limit[band].diffmaglim - self.dmod - up_ext[band]-ext[band],'v',c = col_bands[band],alpha = 0.4)
            ax.invert_yaxis()
            ax1.invert_yaxis()
            fig3.savefig(output_dir+'/'+self.ZTF_ID+'_model_absolute.png', dpi = 100, bbox_inches = 'tight')
            fig4.savefig(output_dir+ '/'+self.ZTF_ID+'_model_apparent.png', dpi = 100, bbox_inches = 'tight')
            
        return mjd_app, mag_app
            
            

    def make_plots_nn(self,results,df_cor,upper_limit,available_bands,upper_limit_bands, samples, output_dir,model_g,model_r,scaler_g,scaler_r,pca_g,pca_r,mean_g,std_g,mean_r,std_r, scaler_i,model_i,pca_i,mean_i,std_i):
        mjd_app = []
        mag_app = []
        plt.rcParams["font.family"] = "serif"
        plt.rc('axes', linewidth = 2)
        plt.rcParams.update({'font.size': 24})
        inds = np.random.randint(len(samples), size=50)
        fine_epo = np.linspace(0,150,100)
        fig3 = plt.figure(figsize=(10,10))
        fig4 = plt.figure(figsize=(10,10))
        median, m_l, m_u = get_params_nn(samples)
        import matplotlib.gridspec as gridspec
        plt.rcParams['xtick.labelsize'] = 20
        plt.rcParams['ytick.labelsize'] = 20
        col = {'g':'#7BC950','r':'#B93327'}
        col_bands = {'g':'#24991E', 'r':'r'}
        up_ext = {'g':self.Ag,'r':self.Ar}
        ax = fig3.add_subplot(111)
        ax1 = fig4.add_subplot(111)
        ext={'g':(median[7]/3.1)*3.303,'r':(median[7]/3.1)*2.285}

        """Making labels for parameters here"""
        
        new_labels =['ZAMS\,(M {_{\odot}})',r' { {E_{k}}\,( {10^{51}} erg)}',
 '{-log{_{10}\,\dot{M}}\,(M {_{\odot}\,yr^{-1}}})',
r'{\beta}',
'^{56}Ni\,(M_{\odot})','CSM Radius (1e14 cm)',
' {t_{exp}\,(day)}',r'{ {A_{V}} (mag)}',r'logZ']

        data = []
        for i in range(8):
            mcmc = np.percentile(samples[:, i], [16, 50, 84])
            q = np.diff(mcmc)
            txt = r"$\rm{{{3}}} = {0:.2f}_{{-{1:.2f}}}^{{{2:.2f}}}$"
            txt_new = txt.format(mcmc[1], q[0], q[1], new_labels[i])
            data.append(txt_new)
            textstr = '\n'.join(data)
            
        "Adding logZ to the plots"
        logZdynesty = results.logz[-1]        
        logZerrdynesty = results.logzerr[-1]
        logz_txt = txt.format(logZdynesty,logZerrdynesty,logZerrdynesty,'logZ')
        textstr = textstr + '\n'+logz_txt
        
        for band in available_bands:
            mag_i = []
            mag_new = NN_interpolate(theta=median[:6],band = band,new_epo = fine_epo,
                                     model_g = model_g,scaler_g=scaler_g, pca_g = pca_g,mean_g=mean_g,std_g=std_g,
                                     model_r=model_r,scaler_r=scaler_r,pca_r=pca_r,mean_r=mean_r,std_r=std_r,
                                     model_i=model_i,scaler_i=scaler_i,pca_i=pca_i,mean_i=mean_i,std_i=std_i)
            obs_new, appar_epoch = new_epoch_gen_nn(df_cor,median,band= band)
            mag_i.append(list(mag_new + self.dmod+up_ext[band]+ext[band]))
            for ind in inds:
                sample = samples[ind]
                mag_th = NN_interpolate(theta=sample[:6],band = band,new_epo = fine_epo,model_g = model_g,model_r=model_r,scaler_g=scaler_g,scaler_r=scaler_r,pca_g = pca_g,pca_r=pca_r,mean_g=mean_g,std_g=std_g,mean_r=mean_r,std_r=std_r)
                app_mag_th = mag_th + self.dmod +up_ext[band]+ext[band]
                mag_i.append(list(app_mag_th))
                ax.plot(fine_epo,mag_th,c = col[band],ls = '--',linewidth = 0.3)#label=theta)
                ax1.plot(appar_epoch,app_mag_th,c = col[band],ls = '--',linewidth = 0.3)#appar_epoch
            mag_app.append(mag_i)
            mjd_app.append(list(appar_epoch))
            ax1.set_ylim(15.0,25)
            ax.set_title(self.ZTF_ID,fontsize = 20)
            ax1.set_title(self.ZTF_ID, fontsize = 20)
            ax1.set_xlim(min(appar_epoch) - 20, max(appar_epoch) +5)
            ax.set_xlim(-10,150)
            ax.set_ylim(-21.0,-10.0)
            ax.set_xlabel('Days from Explosion',fontsize =20)
            ax.set_ylabel('Absolute Magnitude',fontsize = 20)
            ax1.set_xlabel('Modified Julian Date (MJD)',fontsize =20)
            ax1.set_ylabel('Apparent Magnitude',fontsize = 20)
            ax.plot(fine_epo,mag_new,c = col[band],ls = '--',linewidth = 3.0)
            ax1.plot(appar_epoch,mag_new + self.dmod +up_ext[band]+ext[band] ,c = col[band],ls = '--',linewidth = 3.0)#appar_epoch
            ax1.errorbar(df_cor[band].mjd,df_cor[band].magpsf,c = col_bands[band], fmt ='o',ms = '10',yerr = df_cor[band].sigmapsf,label = band + '-ztf',elinewidth=1,markeredgecolor = 'k')
            ax.errorbar(obs_new,df_cor[band].Ab_obs_mag-ext[band],c = col_bands[band], fmt ='o',ms = '10',yerr = df_cor[band].mag_error,label = band+ '-ztf',elinewidth=1,markeredgecolor = 'k')
            ax.legend(prop={'size': 20},loc = 'upper right',bbox_to_anchor=(1.0, 0.98), frameon = False)
            ax1.legend(prop={'size': 20},loc = 'upper right',bbox_to_anchor=(1.0, 0.98), frameon = False)
            ax1.text(0.25, 0.05, textstr, transform=ax1.transAxes, fontsize=15,verticalalignment='bottom',usetex = True,linespacing=2.0)
            ax.text(0.25, 0.05, textstr, transform=ax.transAxes, fontsize=15, verticalalignment='bottom',usetex = True,linespacing=2.0)
            ax.minorticks_on()
            ax.tick_params(axis='both',right=True, top=True, which='both')
            ax.tick_params(axis='both',which='major',direction='in',size=20,labelsize='20',width=3)
            ax.tick_params(axis='both',which='minor',direction='in',size=10,width=3)
            ax.locator_params(axis='x', nbins=5)
            ax.locator_params(axis='y', nbins=5)
            ax1.minorticks_on()
            ax1.tick_params(axis='both',right=True, top=True, which='both')
            ax1.tick_params(axis='both',which='major',direction='in',size=20,labelsize='20',width=3)
            ax1.tick_params(axis='both',which='minor',direction='in',size=10,width=3)
            ax1.locator_params(axis='x', nbins=5)
            ax1.locator_params(axis='y', nbins=5)
            if band in upper_limit_bands:
                ax1.plot(upper_limit[band].mjd,upper_limit[band].diffmaglim,'v',c = col_bands[band],alpha = 0.4)
                ax.plot(upper_limit[band].mjd-df_cor[band].mjd[0]+median[6], upper_limit[band].diffmaglim - self.dmod - up_ext[band]-ext[band],'v',c = col_bands[band],alpha = 0.4)
            ax.invert_yaxis()
            ax1.invert_yaxis()
            fig3.savefig(output_dir+'/'+self.ZTF_ID+'_model_absolute_nn.png', dpi = 100, bbox_inches = 'tight')
            fig4.savefig(output_dir+ '/'+self.ZTF_ID+'_model_apparent_nn.png', dpi = 100, bbox_inches = 'tight')
        return mjd_app, mag_app

