from aiohttp import ClientSession
from lxml.html import HTMLParser, fromstring
from pyquery import PyQuery
from datetime import datetime, timedelta

from .model import Response
from .const import MUSLIMPRO_URL, GEOCODE_URL, AsrjuristicMethod, CalculationMethod, RAMADHAN_API


class Search:
    def __init__(self, session=None, *, lib='asyncio', loop=None, calculation: str = CalculationMethod.DEFAULT.value, asrjuristic: str = AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI.value, **request_kwargs):
        self.request_kwargs = request_kwargs
        self.calculation = calculation
        self.asrjuristic = asrjuristic
        if lib not in ('asyncio'):
            raise ValueError(
                f"lib must be of type `str` and be either `asyncio' not '{lib if isinstance(lib, str) else lib.__class__.__name__}'")
        self._lib = lib
        if lib == 'asyncio':
            from asyncio import get_event_loop
            loop = loop or get_event_loop()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36"
        }
        self.session = session or ClientSession(loop=loop, headers=headers)

    @staticmethod
    def _errors(code):
        if code == 404:
            return "Website down"
        elif code == 302:
            return "Moved temporarily, or blocked by captcha"
        elif code == 403:
            return "Forbidden,or unvalid"
        elif code == 429:
            return "Too many request"
        elif code == 500:
            return "Server error"
        else:
            return "Unknown error, please report to the project maintainer"

    @staticmethod
    def _slice(self, resp: str) -> Response:
        utf8_parser = HTMLParser(encoding='utf-8')
        data = PyQuery(fromstring(resp, parser=utf8_parser))(
            'tbody').eq(0)('tr')
        return Response(data=data, calcMethod=self.calculation, asrjurMethod=self.asrjuristic)

    @staticmethod
    def _slice_ramadhan(resp: PyQuery) -> dict:
        end_date = datetime.strptime(
            f"{resp('td strong').eq(0).text()} {resp('td').eq(2).text()}", '%Y %B %d')

        return {end_date.strftime('%Y'): {
            'start': (end_date - timedelta(days=30)).strftime('%B %d'),
            'end': end_date.strftime('%B %d')
        }
        }

    async def geocode(self, location: str):
        params = {
            'query': location
        }
        response = await self.session.get(GEOCODE_URL, params=params, **self.request_kwargs)
        data = await response.json()
        data = {
            'country_code': data['data'][0]['country_module']['global']['alpha2'],
            'country_name': data['data'][0]['country'],
            'city_name': data['data'][0]['name'],
            'coordinates': f"{data['data'][0]['latitude']},{data['data'][0]['longitude']}",
            'convention': self.calculation,
            'asrjuristic': self.asrjuristic
        } if response.status == 200 else Exception(self._errors(response.status))
        return data

    async def ramadhan_time(self):
        response = await self.session.get(RAMADHAN_API)

        utf8_parser = HTMLParser(encoding='utf-8')
        data = PyQuery(fromstring(await response.text(), parser=utf8_parser)).find('.content_wrapper tbody tr')

        res = {}
        for i in data.items():
            res.update(self._slice_ramadhan(i))

        return res

    async def search(self, location: str):
        geocode = await self.geocode(location=location)
        response = await self.session.get(MUSLIMPRO_URL, params=geocode, **self.request_kwargs)
        return self._slice(self, resp=await response.text()) if response.status == 200 else Exception(self._errors(response.status))
