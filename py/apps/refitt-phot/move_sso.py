'''
move_sso.py

v1.0
May 31 2022

Author: Kathryn E. Weil

Script to rename and move the photometry obtained from Supra Solem Observatory.

'''


from astropy.io import fits
import argparse,os
from pathlib import Path

def parse_args():
    '''Parse command line arguments'''
    parser= argparse.ArgumentParser(description='Move Photometry')
    parser.add_argument('-n','--filename',default=None,help='Fits file name for file to reduce')
    parser.add_argument('-o','--outdirbase',default='/project/amalthea/refitt/photometry/sso/',help='Directory Path for Output Files')
    args = parser.parse_args()
    return args

def move_sso(filename,outdirbase):
    with fits.open(filename,memmap=False,lazy_load_hdus=False) as hdul:
       data = hdul[0].data
       header = hdul[0].header
       filter_raw = header['filter']
       object_name = header['object']
       jd = header['jd']
       outpath=outdirbase+object_name
       filterlist={"g'":'SG',"r'":'SR',"i'":'SI','SG':'SG','SR':'SR','SI':'SI'} #define a mapping from the observed filters to ZTF filters
       if filter_raw in filterlist.keys(): 
           filtername = filterlist[filter_raw]
       else:
        filtername = filter_raw
       outname=object_name+'_sso_0_3m_'+filtername+'_'+str(round(jd,5))+'.fits'
       t=Path(outpath)
       if not t.exists():
           t.mkdir()
       fits.writeto(outpath+'/'+outname,data,header)

if __name__=='__main__':
    args=parse_args()
    move_sso(args.filename,args.outdirbase)



