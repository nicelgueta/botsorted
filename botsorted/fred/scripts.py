import bs4
from typing import (
    List
)
import requests
import math

tennis_url = r'https://www.oddschecker.com/tennis'
headers = headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}


def _get_matches(page: bs4.BeautifulSoup):
    return page.find_all('tr',{'class':'match-on'})

def _get_players(match: bs4.element.Tag) -> List[str]:
    ps = match.find_all('p',{'class':'fixtures-bet-name'})
    return [p.text for p in ps]

def _get_odds(match: bs4.element.Tag, as_str=False) -> List[float]:
    odds = [t.text for t in match.find_all('td',{'class':'basket-add'})]
    return [eval(o) if not as_str else o for o in odds]

def _is_arbitrage(odds: List[float]) -> bool:
    if not len(odds) > 1:
        return False
    return math.prod(odds) > 1

def _is_in_play(match):
    return match.find('span',{'class':'in-play'})

def _get_time(match: bs4.element.Tag, as_str=False):
    return match.find('td',{'class':'time'}).text

def find_tennis_opportunities():
    tennis_html = requests.get(tennis_url,headers=headers).text
    page = bs4.BeautifulSoup(tennis_html, 'html.parser')
    matches = _get_matches(page)
    opps = []
    for match in matches:
        odds = _get_odds(match)
        if _is_arbitrage(odds) and not _is_in_play(match):
            # only take not in play matches with an arb
            names = _get_players(match)
            str_odds = _get_odds(match, True)
            result = math.prod(odds)
            opps.append({
                'Day':match['data-day'],
                'Kick-off':_get_time(match),
                'Player 1':names[0],
                'Player 2':names[1],
                'Player 1 Odds':str_odds[0],
                'Player 2 Odds':str_odds[1],
                'Arb Indicator':round(result,2)
            })
    return opps
