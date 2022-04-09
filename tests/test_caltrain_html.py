#!/usr/bin/env python
# pylint: disable=line-too-long
"""caltrain.html
"""
import os
import typing as T

from bs4 import BeautifulSoup
from requests import post

path = os.path.join(os.path.dirname(__file__), "caltrain.html")

def fetch_html(stn_name: str = "Belmont") -> str:
    """obtain HTML from Caltrain
    """
    head: T.Dict[str, str] = {
        #"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:99.0) Gecko/20100101 Firefox/99.0",
    }
    stn = stn_name.title()
    data = {
        "__CALLBACKID": "ctl09",
        "__CALLBACKPARAM": f"refreshStation={stn}",
        "__VIEWSTATE": "",
        "ipf-st-ip-station": stn,
    }

    url = os.getenv("POST_URL", "https://www.caltrain.com/main.html")
    res = post(url, data=data, headers=head)
    res.raise_for_status()
    txt = res.text
    with open(path, encoding="UTF-8", mode="w") as file:
        file.write(txt)
    return txt

def test():
    """ensure we can parse HTML from Caltrain
    """
    with open(path, encoding="UTF-8", mode="r") as file:
        soup = BeautifulSoup(file.read(), "html.parser")
        #breakpoint()
        print(soup)

        table = soup.find("table", class_="ipf-caltrain-table-trains")
        if table is None:
            div = soup.find("div", "ipf-caltrain-stationselector")  # yuck!
            text = div.findAll(text=True, recursive=False) if div else []
            errs = filter(
                lambda s: s and not s.startswith("<"),  # no HTML
                (s.strip() for s in text),  # error on station page
            )
            err = "; ".join(errs)[:50] or "did not report a specific error message"
            return {}, "Caltrain page: " + err
        head = table.find("tr", class_="ipf-st-ip-trains-table-dir-tr")
        dirs = map(lambda div: div.text.title()[:5], head.find_all("div"))
        both = table.find_all("table", class_="ipf-st-ip-trains-subtable")
        find_text = lambda tr: tuple(td.text for td in tr.find_all("td"))
        find_rows = lambda t: t.find_all("tr", class_="ipf-st-ip-trains-subtable-tr")
        data = dict(zip(dirs, ([find_text(tr) for tr in find_rows(t)] for t in both)))
        # data dict maps SOUTHBOUND or NORTHBOUND to "trains" list (ea. tuple of strings)
        return data, ""

if __name__ == "__main__":
    fetch_html()
    test()
