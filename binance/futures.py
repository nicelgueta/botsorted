import pandas as pd
from .conn import (
    BinanceClient, 
    BASE_URL_FUTURES, 
    make_request,
    BinanceRequest,
    MicroServiceException,
    MAX_LEVERAGE
)
from .models import (
    Interval
)

from ..logger import get_logger

log = get_logger(__name__)

class FuturesClient(BinanceClient):

    def __init__(self):
        super().__init__(BASE_URL_FUTURES)


    ## TEST ################
    @make_request('GET',sig_required=False)
    def ping(self):
        endpoint = '/fapi/v1/ping'
        return BinanceRequest(endpoint=endpoint)

    @make_request('GET',sig_required=False)
    def server_time(self):
        endpoint = '/fapi/v1/time'
        return BinanceRequest(endpoint=endpoint)


    ## GENERAL INFO & MARKET DATA ################
    @make_request('GET',sig_required=False)
    def exchange_info(self):
        endpoint = '/fapi/v1/exchangeInfo'
        return BinanceRequest(endpoint=endpoint)
    
    @make_request('GET',sig_required=False)
    def recent_trades(self,symbol,limit=500):
        endpoint = '/fapi/v1/trades'
        params = {
            'symbol':symbol,
            'limit':limit
        }
        return BinanceRequest(endpoint=endpoint,params=params)
    
    @make_request('GET',sig_required=False)
    def historical_trades(self,symbol,limit=500,fromId=None):
        endpoint = '/fapi/v1/historicalTrades'
        params = {
            'symbol':symbol,
            'limit':limit,
            'fromId':fromId
        }
        return BinanceRequest(endpoint=endpoint,params=params)
    
    @make_request('GET',sig_required=False)
    def get_candles(self,
            symbol,
            interval: str='1d',
            limit: int=500,
            startTime: int=None,
            endTime: int=None):
        endpoint = '/fapi/v1/klines'
        interval = Interval(value=interval).value
        params = {
            'symbol':symbol,
            'limit':limit,
            'interval':interval,
            'startTime':startTime,
            'endTime':endTime
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('GET',sig_required=False)
    def mark_price(self,symbol):
        endpoint = '/fapi/v1/premiumIndex'
        params = {
            'symbol':symbol
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('GET',sig_required=False)
    def depth(self,symbol,limit=500):
        endpoint = '/fapi/v1/depth'
        params = {
            'symbol':symbol,
            'limit':limit
        }
        return BinanceRequest(endpoint=endpoint,params=params)



    ## ACCOUNTS ################
    @make_request('POST',sig_required=True)
    def change_init_leverage(self,symbol:str, leverage:int=1):
        if leverage > MAX_LEVERAGE:
            raise MicroServiceException(
                f'Leverage value of "{leverage}" is too high, '
                f'must be no higher than {MAX_LEVERAGE}'
            )
        endpoint = '/fapi/v1/leverage'
        params ={
            'symbol':symbol,
            'leverage':leverage
        }
        return BinanceRequest(endpoint=endpoint,params=params)
    
    @make_request('POST',sig_required=True)
    def change_margin_type(self,value:int=1):
        if value > MAX_LEVERAGE:
            raise MicroServiceException(
                f'Leverage value of "{value}" is too high, '
                f'must be no higher than {MAX_LEVERAGE}'
            )
        endpoint = '/fapi/v1/leverage'
        params ={
            'value':value
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('GET',sig_required=True,as_df=True)
    def all_orders(self,symbol):
        endpoint = '/fapi/v1/allOrders'
        params = {
            'symbol':symbol
        }
        return BinanceRequest(endpoint=endpoint,params=params)


    @make_request('GET',sig_required=True)
    def balance(self):
        endpoint = '/fapi/v1/balance'
        return BinanceRequest(endpoint=endpoint)


    @make_request('GET',sig_required=True)
    def account(self):
        endpoint = '/fapi/v1/account'
        return BinanceRequest(endpoint=endpoint)
    
    @make_request('GET',sig_required=True)
    def user_trades(self,symbol):
        endpoint = '/fapi/v1/userTrades'
        params = {
            'symbol':symbol
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('GET',sig_required=True)
    def income_history(self):
        endpoint = '/fapi/v1/income'
        return BinanceRequest(endpoint=endpoint)

    @make_request('GET',sig_required=True)
    def get_position_mode(self):
        endpoint = '/fapi/v1/positionSide/dual'
        return BinanceRequest(endpoint=endpoint)

    def get_open_positions(self,as_df: bool=False):
        ac = self.account().json()
        try:
            opens = [p for p in ac['positions'] if float(p['positionAmt'])!=0.00]
        except KeyError:
            opens = []
        if as_df:
            opens = pd.DataFrame(opens)
        return opens
    
    ## TRADING ################
    @make_request('GET',sig_required=True)
    def get_order(self,symbol,orderId):
        endpoint = '/fapi/v1/order'
        params = {
            'symbol':symbol,
            'orderId':orderId
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('DELETE',sig_required=True)
    def cancel_order(self,symbol,orderId):
        endpoint = '/fapi/v1/order'
        params = {
            'symbol':symbol,
            'orderId':orderId
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    @make_request('POST',sig_required=True)
    def new_order(self,symbol,side,quantity,type_='MARKET'):
        endpoint = '/fapi/v1/order'
        params = {
            'symbol':symbol,
            'quantity':quantity,
            'side':side,
            'type':type_
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    def get_current_position(self,symbol:str):
        opens = self.get_open_positions()
        try:
            open_target = [o for o in opens if o['symbol']==symbol][0]
        except IndexError:
            m = 'No open position for given symbol {symbol}'
            log.debug(m)
            return None

        position_base_amt = float(open_target['positionAmt'])
        if position_base_amt < 0:
            #currently short
            return 'short'
        else:
            # currently long
            return 'long'

    def close_position(self,symbol:str):
        # get position base amt for position being closed
        opens = self.get_open_positions()
        try:
            open_target = [o for o in opens if o['symbol']==symbol][0]
        except IndexError:
            m = f'No open position for given symbol {symbol}'
            log.info(m)
            return None
        position_base_amt = float(open_target['positionAmt'])
        if position_base_amt < 0:
            #currently short, so side must be BUY
            side = 'BUY'
        else:
            # currently long, so side must be SELL
            side = 'SELL'
        params = {
            'symbol':symbol,
            'quantity':abs(position_base_amt),
            'side':side
        }
        return self.new_order(**params)
        
        


    #multiples
    @make_request('DELETE',sig_required=True)
    def cancel_all_open_orders(self,symbol):
        endpoint = '/fapi/v1/allOpenOrders'
        params = {
            'symbol':symbol
        }
        return BinanceRequest(endpoint=endpoint,params=params)

    