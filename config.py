from .models import Symbol
import os

DEPLOY_ENV = os.environ['DEPLOY_ENV']

config = {
    'candleColumns':[ #these are in order
        'openTime',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'closeTime',
        'quoteAssetVolume',
        'numberOfTrades',
        'takerBuyBaseAssetVolume',
        'takerBuyQuoteAssetVolume',
        'ignore'
    ],
    'chartTail':1000,
    'exchange':'Binance',
    'interval':'1d',
    'logLevel':'info',
    'maxTradeSizeUSDT':15000,
    'modelLocation':'botsorted/ml/static/grid-boy-wonder.json',
    'modelName':'Reggie',
    'modelStrategy':'futures',
    'modelType':'autogression',
    'modelVersion':'2.0',
    'quantityPrecision':3, #rounding required for order API

    'runTrader':True if DEPLOY_ENV=='HEROKU' else False, #only run the trader on the remote host, not locally as likely testing other stuff

    'sleepInterval':20,
    'symbolTraded':Symbol(base='BTC',quote='USDT'),
    'tradeMarginRatio':0.98, # amount of margin balance to use to calculate base qty required for short trade
    'tradeCallMaxRetries':2,
    'tradeCallWaitTimeSeconds':5,

    # ##################

    'useLiveAccount':True,

    # ##################

    'validIntervals':{
        '1m':60,
        '3m':180,
        '5m':300,
        '15m':900,
        '30m':1800,
        '1h':3600,
        '2h':7200,
        '4h':14400,
        '6h':21600,
        '8h':28800,
        '12h':43200,
        '1d':86400,
        '3d':259200,
        '1w':604800
    },
    'version':'1.5.3'
    
}