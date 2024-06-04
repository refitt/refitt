# -*- coding: utf-8 -*-
"""
Created on April 10 2023

@author: Bhagya M Subrayan
"""

import requests
import json
import csv
import pandas as pd
# Make sure to input the ZTF name as a string
def redshift(ztfid):
    url='https://www.wis-tns.org/api/get/search'
    parameters={ "internal_name": str(ztfid)}
    key='995ac22a4943f6b119de58955c5c4035f9081481'
    YOUR_BOT_ID=92366
    YOUR_BOT_NAME='REFITT_BOT'
    headers={'User-Agent':'tns_marker{"tns_id":'+str(YOUR_BOT_ID)+', "type":"bot",'\
         ' "name":"'+YOUR_BOT_NAME+'"}'}
    search_data={'api_key':key, 'data':json.dumps(parameters)}
    request=requests.post(url,data=search_data,headers=headers)
    
    data=request.json()
    try:
        ID=data['data']['reply'][0]['objname']
        url2='https://www.wis-tns.org/api/get/object'
        parameters2={
        "objname": str(ID),
        "photometry": "1", # “1” or “0” for retrieving or not the associated photometry/spectra
        "spectra": "1"
        }
        search_data2={'api_key':key, 'data':json.dumps(parameters2)}
        request2=requests.post(url2,data=search_data2,headers=headers)
        data2=request2.json()
        Name=data2['data']['reply']['objname']
    
        if data2['data']['reply']['object_type']['name']==None:
            TNSclass='No Classification'
        else:
            TNSclass=data2['data']['reply']['object_type']['name']
        if data2['data']['reply']['redshift']==None:
            TNSredshift='No Redshift'
        else:
            TNSredshift=str(data2['data']['reply']['redshift'])
    except:
        Name='Object Not Found'
        TNSclass='Object Not Found'
        TNSredshift='Object Not Found'
    info={
        "TNS_Name":Name,
        "TNSclass":TNSclass,
        "redshift":TNSredshift
    }
    return(info)