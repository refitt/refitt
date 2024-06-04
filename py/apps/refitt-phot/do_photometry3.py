'''
do_photometry.py

v1.0
May 23 2022

Author: Kathryn E. Weil

Script with preform aperture photometry on transient images 
including the retrevial of template images and doing 
template subtraction. 

The source catalog used for the reference stars is PS1, dr2. 

Adapted from code originally written by Danielle Dickinson

'''

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import keyring
from astroquery.astrometry_net import AstrometryNet

from photutils import SkyCircularAperture,aperture_photometry,SkyCircularAnnulus
from astropy.io import fits
from astropy.stats import sigma_clipped_stats,gaussian_sigma_to_fwhm
from astropy.modeling import models, fitting 
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord, FK5
from astropy.table import Table
from astropy.utils.data import conf
import astropy.units as u
from astroquery.irsa import Irsa
from astroquery.mast import Catalogs
from reproject import reproject_interp
from scipy import stats
from os.path import exists
from REFITT_Obj import REFITT_Obj
from Panstarrs_download import geturl, getimages
from alerce.core import Alerce
alerce = Alerce()

import warnings, sys, wget, subprocess, argparse

'''
params should be updated for each telescope. It will read the telescope name from the headers so the exact name of 'TELESCOP' parameter in the header should be put into the params. If the headers do not contain 'TELESCOP' this system will need to be revisited. For the moment it is configured to use 'OBSERVAT' because Supra Solem TELESCOP parameter in the header is not as expected. 

If it becomes clear that different detector+telescope configurations are common then the instrument can be added to the key of this and the call within main. 

For the parameters:
placescale is a number with units arcsec/pix. 
searchrad is the search radius in units of arcminutes.
mag_high is the brightest magnitude before saturation. 
mag_lwo is the faintest magnitude regularly reached by the facility. 

Each telescope should have its own key, and then a nested dictionary. 

'''
#params={'1.3m McGraw-Hill':{'gain':3.47,'platescale':1.0,'mag_low':19.5,'mag_high':15.0,'searchrad':3.5},\
#        'supra_solem':{'gain':0.247,'platescale':0.919,'mag_low':16.0,'mag_high':13.0,'searchrad':6.5}}

params={'MDM Observatory':{'gain':3.47,'platescale':1.0,'mag_low':19.5,'mag_high':15.0,'searchrad':3.5},\
        'MDM':{'gain':3.47,'platescale':1.0,'mag_low':19.5,'mag_high':15.0,'searchrad':3.5},\
        'Supra Solem Observatory':{'gain':0.247,'platescale':0.919,'mag_low':17.5,'mag_high':13.0,'searchrad':6.5}} ##original searchrad for SSO 6.5

##get the general parameters needed for reduction from the params dictionary above
tel_list = {'1.3m McGraw-Hill':'mdm_1_3m','Supra Solem Observatory':'supra_solem_0_3m','MDM Observatory':'mdm_1_3m','MDM':'mdm_1_3m'} #define a list of telescope to map from the header information to the value from the planner. Please note mdm1.3m is listed twice. The first one is for "TELESCOP" the second is for "OBSERVAT". ##this should only need be updated when you add a new facility to the params directory. 

##### you should not need to change below this
def parse_args():
    '''Parse command line arguments'''
    parser= argparse.ArgumentParser(description='Reduce Photometry')
    parser.add_argument('-n','--filename',default=None,help='Fits file name for file to reduce')
    parser.add_argument('-ztf','--ztf_red',action='store_true',help='Use to invoke ZTF catalog reduction.')
    args = parser.parse_args()
    return args


def phot(data_file):
    
    if exists(data_file):
        pass
    else: 
        print('Datafile does not exist, system exiting: check the file name.')
        sys.exit()
    
    ######Code Below##############
    with fits.open(data_file,memmap=False,lazy_load_hdus=False) as hdul:
    	data = hdul[0].data
    	header = hdul[0].header
    	w = WCS(hdul[0].header)
    	del hdul[0].data
    	del hdul[0].data
    if float((str(w).split('\n')[4]).split(' ')[2])==0.0:
    	ast = AstrometryNet()
    	ast.api_key = 'agaqcxivtugptrwa'
    	new_header = ast.solve_from_image(data_file)
    	new_header['NAXIS1']=header['NAXIS1']
    	new_header['NAXIS2']=header['NAXIS2']
    	new_header['NAXIS'] = 2
    	w = WCS(new_header)
    else:
    	new_header = header
    exp = header['EXPTIME']
    filter_raw = header['filter']
    object_name = header['object']
    print('object'+str(object_name))
    #obj = REFITT_Obj(object_name) #load in the supernova RA/DEC information, last mag, first alert mjd.
    obj = alerce.query_objects(oid = object_name, format = "pandas")
    #sn_coords = SkyCoord(obj.RA*u.deg, obj.DEC*u.deg, frame = "fk5")
    sn_coords = SkyCoord(header['RA'].replace(' ',':'), header['DEC'].replace(' ',':'),unit = (u.hourangle,u.deg), frame = "fk5")
 
    '''
    gainval = float(params[header['TELESCOP']]['gain'])
    platescale = float(params[header['TELESCOP']]['platescale']) *u.arcsec
    mag_low = float(params[header['TELESCOP']]['mag_low'])
    mag_high = float(params[header['TELESCOP']]['mag_high'])
    searchradius =float(params[header['TELESCOP']]['searchrad'])*u.arcminute 
    '''
    gainval = float(params[header['OBSERVAT']]['gain'])
    platescale = float(params[header['OBSERVAT']]['platescale']) *u.arcsec
    mag_low = float(params[header['OBSERVAT']]['mag_low'])
    mag_high = float(params[header['OBSERVAT']]['mag_high'])
    searchradius =float(params[header['OBSERVAT']]['searchrad'])*u.arcminute 
    
    filterlist={'SG':'g','SR':'r','SI':'i',"g'":'g',"r'":"r","i'":"i"} #dictionary to convert from names at Supra Solem to panstarrs
    if filter_raw in filterlist.keys(): filtername=filterlist[filter_raw]
    else: filtername=filter_raw
    
    #base_out=object_name + '_' +tel_list[header['TELESCOP']]+'_'+ filtername + '_' + str(header['jd'])
    base_out='/project/amalthea/refitt/photometry/sso/' + object_name+'/'+object_name + '_' +tel_list[header['OBSERVAT']]+'_'+ filtername + '_' + str(header['jd'])
    print(sn_coords)
    ##check that the supernova coordinates are within the frame of the image:
    
    sn_pix = w.world_to_pixel(sn_coords)
    rows = len(data)
    columns = len(data[0])
    print(sn_coords)
    if sn_pix[0] <= columns and sn_pix[0] > 0 and sn_pix[1] <= rows and sn_pix[1] > 0: pass
    else: 
        print('Supernova Coordinates are not within the image, check supernova name in the header.')
        sys.exit()
          
    object_coords = w.pixel_to_world(columns/2.,rows/2.)

    conf.remote_timeout = 60. #set this higher to avoid time out errors while searching
    
#    df_cat = Catalogs.query_criteria(coordinates=object_coords, radius=searchradius, catalog='PANSTARRS', table='mean', data_release='dr2', nStackDectections=[("gte",2)], columns=['objName', 'objID', 'raMean', 'decMean', filtername+'MeanPSFMag', filtername+'MeanPSFMagErr', filtername+'MeanPSFMagNpt']).to_pandas()
    print(object_coords,searchradius)
    df_c = Catalogs.query_criteria(coordinates=object_coords, radius=searchradius, catalog='PANSTARRS', table='mean', data_release='dr2', nStackDectections=[("gte",2)]).to_pandas()
    df_cat = df_c[['objName', 'objID', 'raMean', 'decMean', filtername+'MeanPSFMag', filtername+'MeanPSFMagErr', filtername+'MeanPSFMagNpt']].copy()
    df_cat = df_cat[df_cat[filtername+'MeanPSFMagNpt']>=2]
    df_cat_all = df_cat[df_cat[filtername+'MeanPSFMag'] <= mag_low]
    df_cat = df_cat[df_cat[filtername+'MeanPSFMag'].between(mag_high,mag_low)]
    df_cat = df_cat.sort_values(by = filtername+'MeanPSFMag')
    df_cat.reset_index(inplace = True,drop = True)
    
    ##Do the aperature photometry to find the zero point, this does not include the supernova:
    positions = SkyCoord(df_cat['raMean'], df_cat['decMean'], unit = 'deg', frame = 'fk5') #all stars for the ZP calculation
    positions_all = SkyCoord(df_cat_all['raMean'], df_cat_all['decMean'], unit = 'deg', frame = 'fk5') ##all stars brighter than mag_low to check for overlapping stars
    pos_pix=positions.to_pixel(w)
    
    #calculate the FWHM

    mean, median, std = sigma_clipped_stats(data, sigma = 3.0)
    xsigma = []
    ysigma = []
    

    i=0
    for k in range(0,len(pos_pix[0])):
        if pos_pix[0][k] > 5 and pos_pix[0][k] < columns-5 and pos_pix[1][k] > 5 and pos_pix[1][k] < rows-5:
            if i < 15:
               z = models.Gaussian2D(amplitude = 10000.-median, 
                                    x_mean = pos_pix[0][k],y_mean = pos_pix[1][k],
                                    x_stddev = 1., y_stddev = 1.)
               #z = models.Gaussian2D(amplitude = median, 
               #                     x_mean = pos_pix[0][k],y_mean = pos_pix[1][k],
               #                     x_stddev = 1., y_stddev = 1.)    
               yi, xi = np.indices(data.shape)
               fit_z = fitting.LevMarLSQFitter()
    
               with warnings.catch_warnings():
            # Ignore model linearity warning from the fitter
            #warnings.simplefilter('ignore')
                   g = fit_z(z, xi, yi, data-median)
    
               xsigma.append(g.x_stddev.value)
               ysigma.append(g.y_stddev.value)
               i=i+1
    
    xsigma = np.asarray(xsigma)
    ysigma = np.asarray(ysigma)
    
    sigma_2D = (ysigma + xsigma)/2.
    sigma_mean, sigma_median, sigma_std = sigma_clipped_stats(sigma_2D, sigma=3, maxiters=3)
    fwhm = sigma_median*gaussian_sigma_to_fwhm    
    
    #define the apertures, in parathensis is pixels, then convert to physical
    ap_rad = (1. * fwhm/2.) * platescale
    ap_rad_l = (3. * fwhm/2.) * platescale
    in_an_rad = (3. * fwhm/2.+3.) * platescale # large apertures plus 3 pixels then convert to pixels
    out_an_rad = (3. * fwhm/2.+6.) * platescale # 3 pixel wide aperture, so start with inner annulus in pixels and add 3

    #Do the aperature photometry to find the zero point, this does not include the supernova:    
    #Small aperture
    aperture = SkyCircularAperture(positions, r = ap_rad)
    pix_aperture = aperture.to_pixel(w) ### in counts
    phot_table = aperture_photometry(data, pix_aperture)
    
    #Large Aperture
    aperture_l = SkyCircularAperture(positions, r = ap_rad_l)
    pix_aperture_l = aperture_l.to_pixel(w) ### in counts
    phot_table_l = aperture_photometry(data, pix_aperture_l)
    
    #Define Background Annulus
    ann_aperture = SkyCircularAnnulus(positions, in_an_rad, out_an_rad)
    pix_ann_aperture = ann_aperture.to_pixel(w) ### in counts

    bkg_mode = []
    bkg_size = []
    bkg_stdev = []
    
    #Determine the Average Background using the annulus:
    annulus_masks = pix_ann_aperture.to_mask(method = 'center')
    for mask in annulus_masks:
        annulus_data = mask.multiply(data)
        annulus_data_1d = annulus_data[mask.data > 0]
        _,_,stdev_sigclip = sigma_clipped_stats(annulus_data_1d)
        annulus_mode = stats.mode(np.ceil(annulus_data_1d))[0][0]
        annulus_size = len(annulus_data_1d)
        bkg_mode.append(annulus_mode)
        bkg_size.append(annulus_size)
        bkg_stdev.append(stdev_sigclip)
    
    
    ##### Convert counts to magnitude, calculate the error. Follow the qphot prescription from IRAF

    phot_table['ann_mode'] = bkg_mode
    phot_table['ann_stdev'] = bkg_stdev
    phot_table['ann_size'] = bkg_size
    phot_table['aper_bkg'] = phot_table['ann_mode'] * pix_aperture.area
    phot_table['flux'] = phot_table['aperture_sum'] - phot_table['aper_bkg']
    phot_table['instr'] = -2.5*np.log10(phot_table['flux']) + 2.5*np.log10(exp)
    phot_table['err'] = np.sqrt(phot_table['flux']/gainval +\
                              pix_aperture.area*phot_table['ann_stdev']**2+\
                              pix_aperture.area**2*phot_table['ann_stdev']**2\
                              /phot_table['ann_size'])
    phot_table['merr'] = 1.0857*phot_table['err']/phot_table['flux']

    phot_table_l['ann_mode'] = bkg_mode
    phot_table_l['ann_stdev'] = bkg_stdev
    phot_table_l['ann_size'] = bkg_size
    phot_table_l['aper_bkg'] = phot_table_l['ann_mode']*pix_aperture_l.area
    phot_table_l['flux'] = phot_table_l['aperture_sum']-phot_table_l['aper_bkg']
    phot_table_l['instr'] = -2.5*np.log10(phot_table_l['flux']) + 2.5*np.log10(exp)
    phot_table_l['err'] = np.sqrt(phot_table_l['flux']/gainval+\
                              pix_aperture_l.area*phot_table_l['ann_stdev']**2+\
                              pix_aperture_l.area**2*phot_table_l['ann_stdev']**2\
                              /phot_table_l['ann_size'])
    phot_table_l['merr'] = 1.0857*phot_table_l['err']/phot_table_l['flux']

    
    
    ##write out a reg file to have location of stars used in the zero point calculation and supernova coordinates
    reg_file_name = base_out + '.reg'
    reg_file = open(reg_file_name,'w')
    reg_file.write("# Region file format: DS9 version 4.1 \n"+"global color=green dashlist=8 3 width=1 font=\"helvetica 10 normal roman\" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1 \n"+"fk5 \n")

    coordinate1 = ('circle(' + str(sn_coords.ra) + ',' + str(sn_coords.dec) + ',' + str(ap_rad.value*3) + '") # color=green\n') ### supernova circle
    reg_file.write(coordinate1)
    
    ##Create arrays to store the zero point, error and difference between large and small for each star, will do averaging of this to get all the values. 
    sums_s = []
    sums_l =[]
    diffs = []
    Mvar_s_arr = [] ### array to store the individual errors from small apertures
    Mvar_l_arr = []
    
    '''
    Loop over each star to determine if it is in included in the ZP. 
    
    For brighter stars use both the large and small apertures to do aperature correction. 
    For fainter stars we will only use the small aperture to determine zero point. 
    
    First check that the instrumental magnitude is not nan, i.e. the background was not larger than the source. 
    
    After check that the sources are not too close to one another by determining the distance between the sources and making sure that the background annulus does not overlap with another source. 
    '''
    for i in range(0,len(phot_table["aperture_sum"])):
        if np.isnan(phot_table['instr'][i])==False and np.isnan(phot_table_l['instr'][i])==False: 
           #A = phot_table_l["aperture_sum"][i]
           #B = phot_table_l["aper_bkg"][i]
           #c = A/B ##this check is for sources that might be on the edge of bright stars
        #print(c)
           T = positions[i] ##check for overlapping sources over the next few lines
           d2d = T.separation(positions_all)
           catalogmsk = d2d < 1.5 * out_an_rad #want to make sure the annulus's for the background do not overlap so we need to include two times, once for each source to avoid overlap.
           idxcatalog = np.where(catalogmsk)[0]
           #print(len(idxcatalog==True))
           if len(idxcatalog==True) <= 1:
           #if len(idxcatalog==True) <= 1 and c < 2: ##remove c for now
               if df_cat[filtername+'MeanPSFMag'][i] <= (mag_low+mag_high)/2.:
                   ZP_s = df_cat[filtername+'MeanPSFMag'][i] - phot_table['instr'][i] #calculate the ZP of the star using the small aperature
                   ZP_l = df_cat[filtername+'MeanPSFMag'][i] - phot_table_l['instr'][i] #calculate the ZP of the star using the large aperature
                   diff = phot_table_l['instr'][i] - phot_table['instr'][i] #large minus small aperture instrumental mag
                   Mvar_s = df_cat[filtername+'MeanPSFMagErr'][i]**2. + phot_table['merr'][i]**2. ##variance of each star used to calculate small aperature
                   Mvar_l = df_cat[filtername+'MeanPSFMagErr'][i]**2. + phot_table_l['merr'][i]**2. ##variance of each star used to calculate large zp
                   diffs.append(diff)
                   sums_s.append(ZP_s)
                   sums_l.append(ZP_l)
                   Mvar_s_arr.append(Mvar_s)
                   Mvar_l_arr.append(Mvar_l)
                   coordinate2 = ('circle(' + str(positions[i].ra) + ',' + str(positions[i].dec) + ',' + str(ap_rad.value*3) + '") # color=red\n') ### star circles
                   reg_file.write(coordinate2)
               elif df_cat[filtername+'MeanPSFMag'][i] > (mag_low+mag_high)/2.:
                   ZP_l = df_cat[filtername+'MeanPSFMag'][i]-phot_table_l['instr'][i]
                   Mvar_l = df_cat[filtername+'MeanPSFMagErr'][i]**2. + phot_table_l['merr'][i]**2. ##variance of each star used to calculate large zp
                   sums_l.append(ZP_l)
                   Mvar_l_arr.append(Mvar_l)
                   coordinate3 = ('circle(' + str(positions[i].ra) + ',' + str(positions[i].dec) + ','+str(ap_rad.value*3) + '") # color=blue\n') ### star circles
                   reg_file.write(coordinate3)
               else: pass

    reg_file.close()

    ##Calculate average ZP and the average error
    Mstd_s = 1/len(Mvar_s_arr)*np.sqrt(np.sum(Mvar_s_arr)) ### 
    ZP_s_avg = np.median(sums_s)

    Mstd_l = 1/len(Mvar_l_arr)*np.sqrt(np.sum(Mvar_l_arr)) ### 
    ZP_l_avg = np.median(sums_l)

    diff_avg = np.median(diffs)
    
    ##get template images
    
    filepath_in_folder=base_out+'_temp_raw.fits'
    ps1_size= int((max(rows,columns)*platescale/(0.25*u.arcsec)).value+100) #determine the size of the panstarrs image from the largest dirction of the image, add 100 pixel buffer to the panstarrs image buffer to ensure reproject has enough pixels and set the value to the nearest integer. 0.25"/pixel is the platescale of PanStarrs.
    #fitsurl = geturl(object_coords.ra.to_string(decimal=True,precision=8), object_coords.dec.to_string(decimal=True,precision=8), size=ps1_size, filters=filtername,format='fits') ##this was the search for the center of the image. 
    fitsurl = geturl(sn_coords.ra.to_string(decimal=True,precision=8), sn_coords.dec.to_string(decimal=True,precision=8), size=ps1_size, filters=filtername,format='fits') #search using SN coordinates to ensure the supernova is in the center. 
    #check if the file exists on disk first then download if it doesn't exist
    if exists(filepath_in_folder): pass
    else: wget.download(fitsurl[0],out=filepath_in_folder)

    file_out_temp = base_out+'_temp.fits'
    diff_out_name = base_out+'_diff.fits'
    print(file_out_temp,diff_out_name)
    with fits.open(filepath_in_folder,memmap=False,lazy_load_hdus=False) as hdul:
       array,footprint = reproject_interp(hdul,new_header)
       hdul[0].header.update(w.to_header(relax=True))
       array2=np.nan_to_num(array,nan=100000)
       if exists(file_out_temp)==False:
           fits.writeto(file_out_temp, array2, hdul[0].header)
           del hdul[0].data
           del hdul[0].data

    ##run hotpants    
    args = ['/project/kaboom/apps/hotpants/hotpants', '-tmplim', file_out_temp, '-inim', data_file, '-outim', diff_out_name, '-c', 't', '-n', 'i','-tl','-10000','-tu','60000','-v','0']
    #args = ['/project/kaboom/apps/hotpants/hotpants', '-tmplim', file_out_temp, '-inim', data_file, '-outim', diff_out_name, '-c', 'i', '-n', 'i','-tl','-10000','-tu','60000','-v','0']
    p = subprocess.run(args,check=True)

    #read in diff image
    with fits.open(diff_out_name,memmap=False,lazy_load_hdus=False) as hdul:
       data2 = hdul[0].data
       del hdul[0].data
       del hdul[0].data

    sn_aperture = SkyCircularAperture(sn_coords, ap_rad)
    pix_sn_aperture = sn_aperture.to_pixel(w)
    sn_phot_table = aperture_photometry(data2, pix_sn_aperture)
    sn_phot_table['aperture_sum'].info.format = '%.8g'  # for consistent table output

    snn_aperture = SkyCircularAnnulus(sn_coords, in_an_rad, out_an_rad)
    pix_snn_aperture = snn_aperture.to_pixel(w)

    sn_ann_masks = pix_snn_aperture.to_mask(method = 'center')
    sn_ann_data = sn_ann_masks.multiply(data2)
    sn_ann_data_1d = sn_ann_data[sn_ann_masks.data > 0]
    _,_,sn_stdev_sigclip = sigma_clipped_stats(sn_ann_data_1d)
    sn_ann_mode = stats.mode(np.ceil(sn_ann_data_1d))[0][0]
    sn_ann_size = len(sn_ann_data_1d)

    sn_phot_table['ann_mode'] = sn_ann_mode
    sn_phot_table['ann_stdev'] = sn_stdev_sigclip
    sn_phot_table['ann_size'] = sn_ann_size
    
    sn_phot_table['aper_bkg'] = sn_phot_table['ann_mode']*pix_sn_aperture.area
    sn_phot_table['flux']=sn_phot_table['aperture_sum']-sn_phot_table['aper_bkg']
    sn_phot_table['instr'] = -2.5*np.log10(sn_phot_table['flux'])+2.5*np.log10(exp)
    sn_phot_table['err'] = np.sqrt(sn_phot_table['flux']/gainval+\
                              pix_aperture.area*sn_phot_table['ann_stdev']**2+\
                              pix_sn_aperture.area**2*sn_phot_table['ann_stdev']**2\
                              /sn_phot_table['ann_size'])
    sn_phot_table['merr'] = 1.0857*sn_phot_table['err']/sn_phot_table['flux']    
    

    sn_phot_table['flux_nb'] = sn_phot_table['aperture_sum']
    sn_phot_table['instr_nb'] = -2.5*np.log10(sn_phot_table['flux_nb'])+2.5*np.log10(exp)
    sn_phot_table['err_nb'] = np.sqrt(sn_phot_table['flux_nb']/gainval+\
                              pix_aperture.area*sn_phot_table['ann_stdev']**2+\
                              pix_sn_aperture.area**2*sn_phot_table['ann_stdev']**2\
                              /sn_phot_table['ann_size'])
    sn_phot_table['merr_nb'] = 1.0857*sn_phot_table['err_nb']/sn_phot_table['flux_nb']


    sn_inst = sn_phot_table['instr'].value
    sn_mag = ZP_l_avg + sn_phot_table['instr'].value+diff_avg
    #sn_mag_no_cor = ZP_s_avg + sn_phot_table['instr'].value
    sn_mag_err = np.sqrt(Mstd_l**2+sn_phot_table['merr']**2).value
    
    sn_inst_nb = sn_phot_table['instr_nb'].value
    sn_mag_nb = ZP_l_avg + sn_phot_table['instr_nb'].value+diff_avg
    sn_mag_nb_err = np.sqrt(Mstd_l**2+sn_phot_table['merr_nb']**2).value
    
    text_out = object_name+'_'+filtername+'.txt'
    print(sn_mag_nb)
    if exists(text_out):
        with open(text_out,'a') as f:
            print(object_name, tel_list[header['OBSERVAT']], filtername, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f)
            #print(object_name, tel_list[header['TELESCOP']], filtername, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f) ##uncomment this line when you switch for the different header keyword
    else:
        with open(text_out,'w') as f:
            print('obj_id', 'telescope', 'filter', 'jd', 'sn_mag', 'sn_mag_err', 'sn_inst', 'sn_mag_nb', 'sn_mag_nb_err', 'sn_inst_nb', 'ZP_l', 'ZP_l_err', 'ZP_s', 'ZP_s_err', 'diff', 'fwhm', file=f)
            print(object_name, tel_list[header['OBSERVAT']], filtername, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f)
            #print(object_name, tel_list[header['TELESCOP']], filtername, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f) ##uncomment this line when you switch for the different header keyword

    #print(object_name, filtername, "jd:", header['jd'], "mag:", round(sn_mag[0],4), "mag err:", round(sn_mag_err[0],3))
    #print("inst", round(sn_inst_mag[0],3), "ZP_l:", round(ZP_l_avg,3), "ZP_l_error:", round(Mstd_l,3))
    #print("ZP_s:", round(ZP_s_avg,3), "ZP_s_error:", round(Mstd_s,3), "Diff L to S:", round(diff_avg,3))
    #print("SN_mag_no_corr:", round(sn_mag_no_cor[0],3))

def phot_ztf(data_file):
    
    if exists(data_file):
        pass
    else: 
        print('Datafile does not exist, system exiting: check the file name.')
        sys.exit()
    
    ######Code Below##############
    with fits.open(data_file) as hdul:
    	data = hdul[0].data
    	header = hdul[0].header
    w = WCS(header)
    exp = header['EXPTIME']
    filter_raw = header['filter']
    object_name = header['object']
    
    obj = REFITT_Obj(object_name) #load in the supernova RA/DEC information, last mag, first alert mjd.
    
    sn_coords = SkyCoord(obj.RA*u.deg, obj.DEC*u.deg, frame = "fk5")
    '''
    gainval = float(params[header['TELESCOP']]['gain'])
    platescale = float(params[header['TELESCOP']]['platescale']) *u.arcsec
    mag_low = float(params[header['TELESCOP']]['mag_low'])
    mag_high = float(params[header['TELESCOP']]['mag_high'])
    searchradius =float(params[header['TELESCOP']]['searchrad'])*u.arcminute 
    '''
    gainval = float(params[header['OBSERVAT']]['gain'])
    platescale = float(params[header['OBSERVAT']]['platescale']) *u.arcsec
    mag_low = float(params[header['OBSERVAT']]['mag_low'])
    mag_high = float(params[header['OBSERVAT']]['mag_high'])
    searchradius =float(params[header['OBSERVAT']]['searchrad'])*u.arcminute 

    filterlist_ztf={'g':'zg','r':'zr','i':'zi','SG':'zg','SR':'zr','SI':'zi',"g'":"zg","r'":"zr","i'":"zi"} #define a mapping from the observed filters to ZTF filters
    if filter_raw in filterlist_ztf.keys(): 
        filtername_ztf = filterlist_ztf[filter_raw]
    else: 
        print('Filter names from headers do not map to ZTF.') 
        sys.exit()
    
    base_out=object_name + '_' +tel_list[header['OBSERVAT']]+'_'+ filtername_ztf + '_' + str(header['jd'])
    #base_out=object_name + '_' +tel_list[header['TELESCOP']]+'_'+ filtername_ztf + '_' + str(header['jd'])
    
    ##check that the supernova coordinates are within the frame of the image:
    sn_pix = w.world_to_pixel(sn_coords)
    rows = len(data)
    columns = len(data[0])
    
    if sn_pix[0] <= columns and sn_pix[0] > 0 and sn_pix[1] <= rows and sn_pix[1] > 0: pass
    else: 
        print('Supernova Coordinates are not within the image, check supernova name in the header.')
        sys.exit()
          
    object_coords = w.pixel_to_world(rows/2.,columns/2.)

    conf.remote_timeout = 45. #set this higher to avoid time out errors while searching
    
    #search for ZTF template image, make sure at least one image exists in the filter you are searching with. 
    try:
    	url1="https://irsa.ipac.caltech.edu/ibe/search/ztf/products/sci?WHERE=filtercode='"+filtername_ztf+"'&POS="+object_coords.ra.to_string(decimal=True)+','+object_coords.dec.to_string(decimal=True)+"&mcen&ct=ipac_table"
    	df1=Table.read(url1,format='ipac').to_pandas()
    except:
    	print('No ZTF Templates available for this object. Exiting')
    	sys.exit()
    
    fieldvalue=df1['field'].item()

    ##find the catalog stars:
    Irsa.ROW_LIMIT=100000
    df_cat =Irsa.query_region(object_coords.ra.to_string(decimal=True) + ',' + object_coords.dec.to_string(decimal=True), catalog = 'ztf_objects_dr10', radius = searchradius, spatial = "Cone").to_pandas() 
    df_cat = df_cat[df_cat['filtercode']==filtername_ztf]
    df_cat = df_cat[df_cat['field'] == fieldvalue] #eliminate multiple measurements of stars, take all in only the field of the template image determined above
    df_cat = df_cat[df_cat.medmagerr.notnull()] #make sure it has been measured more than once
    df_cat_all = df_cat[df_cat['medianmag'] <= mag_low] ##all stars
    df_cat = df_cat[df_cat['medianmag'].between(mag_high,mag_low)] ##set to avoid saturated stars in the MDM image
    df_cat = df_cat.sort_values(by = 'medianmag')
    df_cat.reset_index(inplace = True,drop = True)
    
    ##Do the aperature photometry to find the zero point, this does not include the supernova:
    positions = SkyCoord(df_cat['ra'], df_cat['dec'], unit = 'deg', frame = 'fk5') #all stars for the ZP calculation
    positions_all = SkyCoord(df_cat_all['ra'], df_cat_all['dec'], unit = 'deg', frame = 'fk5') ##all stars brighter than mag_low to check for overlapping stars
    pos_pix=positions.to_pixel(w)
    
    #calculate the FWHM
    mean, median, std = sigma_clipped_stats(data, sigma = 3.0)
    xsigma = []
    ysigma = []

    for k in range(0,len(pos_pix[0])):
        if k <= 16:
            z = models.Gaussian2D(amplitude = 10000.-median, 
                                    x_mean = pos_pix[0][k],y_mean = pos_pix[1][k],
                                    x_stddev = 1., y_stddev = 1.)
    
            yi, xi = np.indices(data.shape)
            fit_z = fitting.LevMarLSQFitter()
    
            with warnings.catch_warnings():
            # Ignore model linearity warning from the fitter
            #warnings.simplefilter('ignore')
                g = fit_z(z, xi, yi, data-median)
    
            xsigma.append(g.x_stddev.value)
            ysigma.append(g.y_stddev.value)
    
    xsigma = np.asarray(xsigma)
    ysigma = np.asarray(ysigma)
    
    sigma_2D = (ysigma + xsigma)/2.
    sigma_mean, sigma_median, sigma_std = sigma_clipped_stats(sigma_2D, sigma=3, maxiters=3)
    fwhm = sigma_median*gaussian_sigma_to_fwhm    
    
    #define the apertures, in parathensis is pixels, then convert to physical
    ap_rad = (1. * fwhm/2.) * platescale
    ap_rad_l = (3. * fwhm/2.) * platescale
    in_an_rad = (3. * fwhm/2.+3.) * platescale # large apertures plus 3 pixels then convert to pixels
    out_an_rad = (3. * fwhm/2.+6.) * platescale # 3 pixel wide aperture, so start with inner annulus in pixels and add 3

    #Do the aperature photometry to find the zero point, this does not include the supernova:    
    #Small aperture
    aperture = SkyCircularAperture(positions, r = ap_rad)
    pix_aperture = aperture.to_pixel(w) ### in counts
    phot_table = aperture_photometry(data, pix_aperture)
    
    #Large Aperture
    aperture_l = SkyCircularAperture(positions, r = ap_rad_l)
    pix_aperture_l = aperture_l.to_pixel(w) ### in counts
    phot_table_l = aperture_photometry(data, pix_aperture_l)
    
    #Define Background Annulus
    ann_aperture = SkyCircularAnnulus(positions, in_an_rad, out_an_rad)
    pix_ann_aperture = ann_aperture.to_pixel(w) ### in counts

    bkg_mode = []
    bkg_size = []
    bkg_stdev = []
    
    #Determine the Average Background using the annulus:
    annulus_masks = pix_ann_aperture.to_mask(method = 'center')
    for mask in annulus_masks:
        annulus_data = mask.multiply(data)
        annulus_data_1d = annulus_data[mask.data > 0]
        _,_,stdev_sigclip = sigma_clipped_stats(annulus_data_1d)
        annulus_mode = stats.mode(np.ceil(annulus_data_1d))[0][0]
        annulus_size = len(annulus_data_1d)
        bkg_mode.append(annulus_mode)
        bkg_size.append(annulus_size)
        bkg_stdev.append(stdev_sigclip)
    
    
    ##### Convert counts to magnitude, calculate the error. Follow the qphot prescription from IRAF

    phot_table['ann_mode'] = bkg_mode
    phot_table['ann_stdev'] = bkg_stdev
    phot_table['ann_size'] = bkg_size
    phot_table['aper_bkg'] = phot_table['ann_mode'] * pix_aperture.area
    phot_table['flux'] = phot_table['aperture_sum'] - phot_table['aper_bkg']
    phot_table['instr'] = -2.5*np.log10(phot_table['flux']) + 2.5*np.log10(exp)
    phot_table['err'] = np.sqrt(phot_table['flux']/gainval +\
                              pix_aperture.area*phot_table['ann_stdev']**2+\
                              pix_aperture.area**2*phot_table['ann_stdev']**2\
                              /phot_table['ann_size'])
    phot_table['merr'] = 1.0857*phot_table['err']/phot_table['flux']

    phot_table_l['ann_mode'] = bkg_mode
    phot_table_l['ann_stdev'] = bkg_stdev
    phot_table_l['ann_size'] = bkg_size
    phot_table_l['aper_bkg'] = phot_table_l['ann_mode']*pix_aperture_l.area
    phot_table_l['flux'] = phot_table_l['aperture_sum']-phot_table_l['aper_bkg']
    phot_table_l['instr'] = -2.5*np.log10(phot_table_l['flux']) + 2.5*np.log10(exp)
    phot_table_l['err'] = np.sqrt(phot_table_l['flux']/gainval+\
                              pix_aperture_l.area*phot_table_l['ann_stdev']**2+\
                              pix_aperture_l.area**2*phot_table_l['ann_stdev']**2\
                              /phot_table_l['ann_size'])
    phot_table_l['merr'] = 1.0857*phot_table_l['err']/phot_table_l['flux']

    ##write out a reg file to have location of stars used in the zero point calculation and supernova coordinates
    reg_file_name = base_out + '.reg'
    reg_file = open(reg_file_name,'w')
    reg_file.write("# Region file format: DS9 version 4.1 \n"+"global color=green dashlist=8 3 width=1 font=\"helvetica 10 normal roman\" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1 \n"+"fk5 \n")

    coordinate1 = ('circle(' + str(sn_coords.ra) + ',' + str(sn_coords.dec) + ',' + str(ap_rad.value*3) + '") # color=green\n') ### supernova circle
    reg_file.write(coordinate1)
    
    ##Create arrays to store the zero point, error and difference between large and small for each star, will do averaging of this to get all the values. 
    sums_s = []
    sums_l =[]
    diffs = []
    Mvar_s_arr = [] ### array to store the individual errors from small apertures
    Mvar_l_arr = []
    
    '''
    Loop over each star to determine if it is in included in the ZP. 
    
    For brighter stars use both the large and small apertures to do aperature correction. 
    For fainter stars we will only use the small aperture to determine zero point. 
    
    First check that the instrumental magnitude is not nan, i.e. the background was not larger than the source. 
    
    After check that the sources are not too close to one another by determining the distance between the sources and making sure that the background annulus does not overlap with another source. 
    '''
    for i in range(0,len(phot_table["aperture_sum"])):
        if np.isnan(phot_table['instr'][i])==False and np.isnan(phot_table_l['instr'][i])==False: 
           #A = phot_table_l["aperture_sum"][i]
           #B = phot_table_l["aper_bkg"][i]
           #c = A/B ##this check is for sources that might be on the edge of bright stars
        #print(c)
           T = positions[i] ##check for overlapping sources over the next few lines
           d2d = T.separation(positions_all)
           catalogmsk = d2d < 1.5 * out_an_rad #want to make sure the annulus's for the background do not overlap so we need to include two times, once for each source to avoid overlap.
           idxcatalog = np.where(catalogmsk)[0]
           #print(len(idxcatalog==True))
           if len(idxcatalog==True) <= 1:
           #if len(idxcatalog==True) <= 1 and c < 2: ##remove c for now
               if df_cat['medianmag'][i] <= (mag_low+mag_high)/2.:
                   ZP_s = df_cat['medianmag'][i] - phot_table['instr'][i] #calculate the ZP of the star using the small aperature
                   ZP_l = df_cat['medianmag'][i] - phot_table_l['instr'][i] #calculate the ZP of the star using the large aperature
                   diff = phot_table_l['instr'][i] - phot_table['instr'][i] #large minus small aperture instrumental mag
                   Mvar_s = df_cat['medmagerr'][i]**2. + phot_table['merr'][i]**2. ##variance of each star used to calculate small aperature
                   Mvar_l = df_cat['medmagerr'][i]**2. + phot_table_l['merr'][i]**2. ##variance of each star used to calculate large zp
                   diffs.append(diff)
                   sums_s.append(ZP_s)
                   sums_l.append(ZP_l)
                   Mvar_s_arr.append(Mvar_s)
                   Mvar_l_arr.append(Mvar_l)
                   coordinate2 = ('circle(' + str(positions[i].ra) + ',' + str(positions[i].dec) + ',' + str(ap_rad.value*3) + '") # color=red\n') ### star circles
                   reg_file.write(coordinate2)
               elif df_cat['medianmag'][i] > (mag_low+mag_high)/2.:
                   ZP_l = df_cat['medianmag'][i]-phot_table_l['instr'][i]
                   Mvar_l = df_cat['medmagerr'][i]**2. + phot_table_l['merr'][i]**2. ##variance of each star used to calculate large zp
                   sums_l.append(ZP_l)
                   Mvar_l_arr.append(Mvar_l)
                   coordinate3 = ('circle(' + str(positions[i].ra) + ',' + str(positions[i].dec) + ','+str(ap_rad.value*3) + '") # color=blue\n') ### star circles
                   reg_file.write(coordinate3)
               else: pass

    reg_file.close()

    ##Calculate average ZP and the average error
    Mstd_s = 1/len(Mvar_s_arr)*np.sqrt(np.sum(Mvar_s_arr)) ### 
    ZP_s_avg = np.median(sums_s)

    Mstd_l = 1/len(Mvar_l_arr)*np.sqrt(np.sum(Mvar_l_arr)) ### 
    ZP_l_avg = np.median(sums_l)

    diff_avg = np.median(diffs)
    

    ##want to download the template image for host subtraction to improve the photometry:

    #first use the catalog values from earlier to define the search for the correct template images:
    ##need to pad the numbers to satisfy ZTF search standards
    pad_field_zeros = []
    if len(str(df_cat['field'].values[0])) < 6:
        zeros_add = 6-len(str(df_cat['field'].values[0]))
        for n in range(0,zeros_add):
            pad_field_zeros.append('0')
        paddedfield = ''.join(pad_field_zeros) + str(df_cat['field'].values[0])
    else: paddedfield = str(df_cat['field'].values[0])

    pad_ccdid_zeros = []
    if len(str(df_cat['ccdid'].values[0])) < 2:
        zeros_add = 6-len(str(df_cat['ccdid'].values[0]))
        for n in range(0,zeros_add):
            pad_ccdid_zeros.append('0')
        paddedccdid = ''.join(pad_ccdid_zeros)+str(df_cat['ccdid'].values[0])
    else: paddedccdid=str(df_cat['ccdid'].values[0])

    qid = str(df_cat['qid'].values[0])

    url = "https://irsa.ipac.caltech.edu/ibe/search/ztf/products/sci?WHERE=field="+paddedfield+"+AND+ccdid="+paddedccdid+"+AND+filtercode='"+filtername_ztf+"'+AND+qid="+qid

    df2 = Table.read(url,format = 'ipac').to_pandas()

    #preform filtering to get a template image that is deep, with decent seeing and before the time of explosion
    df2 = df2[df2['maglimit'] >= np.median(df2['maglimit'])]
    df2 = df2[df2['obsjd'] <= (obj.locus.properties['oldest_alert_observation_time'] + 2400000.5 - 30.)] #use 30 days before first alert to try to avoid contamination from any pre-explosion activity
    df2 = df2[df2['obsjd'] == df2['obsjd'].max()]
    df2 = df2[df2['seeing'] == df2['seeing'].min()]

    filefracdaystr = str(df2['filefracday'].values[0])
    str_arr = list(filefracdaystr)
    year = ''.join(str_arr[0:4])
    month = ''.join(str_arr[4:6])
    day = ''.join(str_arr[6:8])
    fracday = ''.join(str_arr[8:])
    imgtypecode = str(df2['imgtypecode'].values[0])
    filtercode = str(df2['filtercode'].values[0])
    qid = str(df2['qid'].values[0])
    
    #need to do this again because the search and the images uses a different number of zeros. 
    pad_ccdid_zeros = []
    if len(str(df2['ccdid'].values[0])) < 2:
        zeros_add_ccd = 2 - len(str(df2['ccdid'].values[0]))
        for n in range(0,zeros_add_ccd):
            pad_ccdid_zeros.append('0')
        paddedccdid = ''.join(pad_ccdid_zeros) + str(df2['ccdid'].values[0])
    else: paddedccdid = str(df2['ccdid'].values[0])
    

    suffix = 'sciimg.fits'

    filepath_url = 'https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/'+year+'/'+month+day+'/'+fracday+'/ztf_'+filefracdaystr+'_'+paddedfield+'_'+filtername_ztf+'_c'+paddedccdid+'_'+imgtypecode+'_q'+qid+'_'+suffix

    filepath_in_folder = 'ztf_'+filefracdaystr+'_'+paddedfield+'_'+filtername_ztf+'_c'+paddedccdid+'_'+imgtypecode+'_q'+qid+'_'+suffix
    
    #check if the file exists on disk first then download if it doesn't exist
    if exists(filepath_in_folder): pass
    else: wget.download(filepath_url)

    file_out_temp = base_out+'_temp.fits'
    diff_out_name = base_out+'_diff.fits'

    ##Open template image and reproject to same coordinates as the observed image
    with fits.open(filepath_in_folder) as hdul:
        array,footprint = reproject_interp(hdul,header)
        hdul[0].header.update(w.to_header(relax=True))
        array2=np.nan_to_num(array,nan=100000)
        fits.writeto(file_out_temp, array2, hdul[0].header)

    ##run hotpants    
    args = ['/project/kaboom/apps/hotpants/hotpants', '-tmplim', file_out_temp, '-inim', data_file, '-outim', diff_out_name, '-c', 't', '-n', 'i','-tu','99999','-v','0']
    p = subprocess.run(args,check=True)

    #read in diff image
    with fits.open(diff_out_name) as hdul:
        data2 = hdul[0].data

    sn_aperture = SkyCircularAperture(sn_coords, ap_rad)
    pix_sn_aperture = sn_aperture.to_pixel(w)
    sn_phot_table = aperture_photometry(data2, pix_sn_aperture)
    sn_phot_table['aperture_sum'].info.format = '%.8g'  # for consistent table output

    snn_aperture = SkyCircularAnnulus(sn_coords, in_an_rad, out_an_rad)
    pix_snn_aperture = snn_aperture.to_pixel(w)

    sn_ann_masks = pix_snn_aperture.to_mask(method = 'center')
    sn_ann_data = sn_ann_masks.multiply(data2)
    sn_ann_data_1d = sn_ann_data[sn_ann_masks.data > 0]
    _,_,sn_stdev_sigclip = sigma_clipped_stats(sn_ann_data_1d)
    sn_ann_mode = stats.mode(np.ceil(sn_ann_data_1d))[0][0]
    sn_ann_size = len(sn_ann_data_1d)

    sn_phot_table['ann_mode'] = sn_ann_mode
    sn_phot_table['ann_stdev'] = sn_stdev_sigclip
    sn_phot_table['ann_size'] = sn_ann_size
    
    sn_phot_table['aper_bkg'] = sn_phot_table['ann_mode']*pix_sn_aperture.area
    sn_phot_table['flux']=sn_phot_table['aperture_sum']-sn_phot_table['aper_bkg']
    sn_phot_table['instr'] = -2.5*np.log10(sn_phot_table['flux'])+2.5*np.log10(exp)
    sn_phot_table['err'] = np.sqrt(sn_phot_table['flux']/gainval+\
                              pix_aperture.area*sn_phot_table['ann_stdev']**2+\
                              pix_sn_aperture.area**2*sn_phot_table['ann_stdev']**2\
                              /sn_phot_table['ann_size'])
    sn_phot_table['merr'] = 1.0857*sn_phot_table['err']/sn_phot_table['flux']    
    

    sn_phot_table['flux_nb'] = sn_phot_table['aperture_sum']
    sn_phot_table['instr_nb'] = -2.5*np.log10(sn_phot_table['flux_nb'])+2.5*np.log10(exp)
    sn_phot_table['err_nb'] = np.sqrt(sn_phot_table['flux_nb']/gainval+\
                              pix_aperture.area*sn_phot_table['ann_stdev']**2+\
                              pix_sn_aperture.area**2*sn_phot_table['ann_stdev']**2\
                              /sn_phot_table['ann_size'])
    sn_phot_table['merr_nb'] = 1.0857*sn_phot_table['err_nb']/sn_phot_table['flux_nb']


    sn_inst = sn_phot_table['instr'].value
    sn_mag = ZP_l_avg + sn_phot_table['instr'].value+diff_avg
    #sn_mag_no_cor = ZP_s_avg + sn_phot_table['instr'].value
    sn_mag_err = np.sqrt(Mstd_l**2+sn_phot_table['merr']**2).value
    
    sn_inst_nb = sn_phot_table['instr_nb'].value
    sn_mag_nb = ZP_l_avg + sn_phot_table['instr_nb'].value+diff_avg
    sn_mag_nb_err = np.sqrt(Mstd_l**2+sn_phot_table['merr_nb']**2).value
    
    text_out = object_name+'_'+filtername_ztf+'.txt'

    if exists(text_out):
        with open(text_out,'a') as f:
            print(object_name, tel_list[header['OBSERVAT']], filtername_ztf, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f)
            #print(object_name, tel_list[header['TELESCOP']], filtername_ztf, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f) ##uncomment this line when you switch for the different header keyword
    else:
        with open(text_out,'w') as f:
            print('obj_id', 'telescope', 'filter', 'jd', 'sn_mag', 'sn_mag_err', 'sn_inst', 'sn_mag_nb', 'sn_mag_nb_err', 'sn_inst_nb', 'ZP_l', 'ZP_l_err', 'ZP_s', 'ZP_s_err', 'diff', 'fwhm', file=f)
            print(object_name, tel_list[header['OBSERVAT']], filtername_ztf, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f)
            #print(object_name, tel_list[header['TELESCOP']], filtername_ztf, header['jd'], round(sn_mag[0],4), round(sn_mag_err[0],4), round(sn_inst[0],4), round(sn_mag_nb[0],4), round(sn_mag_nb_err[0],4), round(sn_inst_nb[0],4), round(ZP_l_avg,4), round(Mstd_l,4), round(ZP_s_avg,4), round(Mstd_s,4), round(diff_avg,4),round(fwhm*platescale.value,4), file=f) ##uncomment this line when you switch for the different header keyword

    #print(object_name, filtername, "jd:", header['jd'], "mag:", round(sn_mag[0],4), "mag err:", round(sn_mag_err[0],3))
    #print("inst", round(sn_inst_mag[0],3), "ZP_l:", round(ZP_l_avg,3), "ZP_l_error:", round(Mstd_l,3))
    #print("ZP_s:", round(ZP_s_avg,3), "ZP_s_error:", round(Mstd_s,3), "Diff L to S:", round(diff_avg,3))
    #print("SN_mag_no_corr:", round(sn_mag_no_cor[0],3))

if __name__=='__main__':
    args=parse_args()
    if args.ztf_red==True: phot_ztf(args.filename)
    else: phot(args.filename)
