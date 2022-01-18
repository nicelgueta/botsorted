from typing import Optional
import datetime
import pandas as pd
import pytz

from fastapi import FastAPI, Request
from threading import Thread
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.utils import get_openapi

# trading
from .trading.engine import TradingEngine
from .config import config
from .trading.cli import TradingClient

# arbitrage
from .fred.scripts import find_tennis_opportunities

#vis
from .bsutils.viz import DataVisualiser
from .ml.dr import DirectReinforcementModel

trader = TradingEngine(model_path=config["modelLocation"])

app = FastAPI()

app.mount("/static", StaticFiles(directory="build/static"), name="static")
templates = Jinja2Templates(directory="build")

app.trading_thread = Thread(target=trader.run_trading_loop)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Botsorted",
        version=config["version"],
        description="None currently implemented",
        routes=app.routes,
    )
    # openapi_schema["info"]["x-logo"] = {
    #     "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    # }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# start trading
if config["runTrader"]:
    app.trading_thread.start()


@app.get("/ping", include_in_schema=False)
async def ping():
    return {"message": "hello"}



@app.get('/tennis',response_class=HTMLResponse, include_in_schema=False)
async def tennis(request: Request):
    opps = find_tennis_opportunities()
    # turn into html
    html= pd.DataFrame(opps).to_html(
        index=False,
        justify='center',
        classes=['arbtable']
    )
    local_tz = pytz.timezone("Europe/London")
    return templates.TemplateResponse("tennis_page.html", {
        'request':request,
        'homeBaseUrl':'https://botsorted.herokuapp.com',
        'currentDate':datetime.datetime.now(local_tz).strftime("%d/%m/%Y, %H:%M:%S %Z"),
        'results':html
    })

@app.get('/getPerformance', response_class=HTMLResponse, include_in_schema=False)
async def get_performance(request: Request):
    cli = TradingClient()
    data = cli.df_candles(config["symbolTraded"], limit=1500)
    data.close = data.close.astype(float)
    chartHtml, chartData = DataVisualiser.plot_perf(data, trader.model)
    start_date = datetime.datetime.fromisoformat(
        chartData.closeTimeIso[chartData.index[1]]
    ).date()
    start_price = chartData.close[chartData.index[0]]

    # compute extra charts data depending on what we have configed
    extraCharts = [
        {
            **ec,
            **{
                "html": DataVisualiser.plot_perf(
                    data,
                    DirectReinforcementModel.from_json(ec["modelLocation"]),
                    modelName=f"{ec['modelName']} v{ec['modelVersion']}",
                )[0]
            },
        }
        for ec in config["extraCharts"]
    ]
    return templates.TemplateResponse(
        "chart_page.html",
        {
            "request": request,
            "homeBaseUrl": "https://botsorted.herokuapp.com",
            "chartHtml": chartHtml,
            "modelVersion": config["modelVersion"],
            "modelName": config["modelName"],
            "extraCharts": extraCharts,
            "startDate": start_date,
            "startPrice": round(start_price, 2),
        },
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "splash.html",
        {
            "request": request,
            "homeBaseUrl": "https://botsorted.herokuapp.com",
            "modelVersion": config["modelVersion"],
            "modelName": config["modelName"],
        },
    )
