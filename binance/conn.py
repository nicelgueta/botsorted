
import os
import functools
import hmac
import time
import hashlib
import requests
import json
from urllib.parse import urlencode

from pydantic import BaseModel #pylint: disable=no-name-in-module
from typing import (
    Optional
)
import pandas as pd
#customs
from ..logger import get_logger
from ..config import config

# *******************
# *******************
USE_LIVE = config['useLiveAccount']
# *******************
# *******************


if os.environ['DEPLOY_ENV']=='HEROKU' and USE_LIVE:
    proxyDict = {
              "http"  : os.environ.get('FIXIE_URL', ''),
              "https" : os.environ.get('FIXIE_URL', '')
            }


BASE_URL = 'https://api.binance.com'
BASE_URL_FUTURES = 'https://fapi.binance.com'
BINANCE_API_KEY = os.environ['BINANCE_API_KEY']
BINANCE_API_SECRET = os.environ['BINANCE_API_SECRET']

BASE_URL_FUTURES_TEST = 'https://testnet.binancefuture.com'
BINANCE_TESTNET_API_KEY = os.environ['BINANCE_TESTNET_API_KEY']
BINANCE_TESTNET_API_SECRET = os.environ['BINANCE_TESTNET_API_SECRET']


RECV_WINDOW = 5000
MAX_LEVERAGE = 5

log = get_logger(__name__)

class MicroServiceException(Exception):
    pass

class BinanceRequest(BaseModel):
    endpoint: str
    params: Optional[dict]

def make_request(method_type,sig_required=False,as_df=False):
    def decorator_repeat(method):
        @functools.wraps(method)
        def inner(self,*args, **kwargs):
            #get method-specific params
            breq = method(self,*args,**kwargs)
            endpoint,params = breq.endpoint,breq.params

            if sig_required:
                resp = self.send_signed_request(method_type,endpoint,params)
            else:
                resp = self.send_public_request(endpoint,params)
            if as_df:
                resp = pd.DataFrame(resp.json())
            # if not (resp.status_code > 199 and resp.status_code < 300):
            #     msg = f'API FAILURE: {method} call FAILED - api return: {resp.json()}'
            #     log.error(msg)
            #     raise MicroServiceException(msg)
            return resp
        return inner
    return decorator_repeat


class BinanceClient(object):

    def __init__(self,url=BASE_URL):
        if USE_LIVE and os.environ['DEPLOY_ENV']=='HEROKU':
            self.api_key=BINANCE_API_KEY
            self.secret_key=BINANCE_API_SECRET
            self.url=url
        else:
            self.api_key=BINANCE_TESTNET_API_KEY
            self.secret_key=BINANCE_TESTNET_API_SECRET
            self.url = BASE_URL_FUTURES_TEST

    # used for sending request requires the signature
    def send_signed_request(self,http_method, url_path, payload={}):
        if not payload:
            payload = {}
        else:
            payload = self.filter_dict(payload) #filter out optional none so not encoded as none
        query_string = urlencode(payload)
        # replace single quote to double quote
        query_string = query_string.replace('%27', '%22')
        if query_string:
            query_string = "{}&timestamp={}".format(query_string, self.__get_timestamp())
        else:
            query_string = 'timestamp={}'.format(self.__get_timestamp())

        url = self.url + url_path + '?' + query_string + '&signature=' + self.__hashing(query_string)
        log.debug("{} {}".format(http_method, url))
        params = {'url': url, 'params': {}}
        
        if os.environ['DEPLOY_ENV']=='HEROKU' and USE_LIVE:
            #only make a request using fixie when absolutely necessary
            response = self.__dispatch_request(http_method)(proxies=proxyDict,**params)
        else:
            response = self.__dispatch_request(http_method)(**params)
        return response

    # used for sending public data request
    def send_public_request(self,url_path, payload=None):
        if not payload:
            payload = {}
        else:
            payload = self.filter_dict(payload) #filter out optional none so not encoded as none
        query_string = urlencode(payload, True)
        url = self.url + url_path
        if query_string:
            url = url + '?' + query_string
        log.debug("{}".format(url))
        response = self.__dispatch_request('GET')(url=url)
        return response


    def __dispatch_request(self,http_method):
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json;charset=utf-8',
            'X-MBX-APIKEY': self.api_key
        })
        return {
            'GET': session.get,
            'DELETE': session.delete,
            'PUT': session.put,
            'POST': session.post,
        }.get(http_method, 'GET')

    def __hashing(self,query_string):
        return hmac.new(
            self.secret_key.encode('utf-8'), 
            query_string.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def __get_timestamp(self):
        return int(time.time() * 1000)

    @staticmethod
    def filter_dict(dic):
        return {k:v for k,v in dic.items() if v is not None}       
    