from aiohttp import ClientSession
from lxml.html import HTMLParser, fromstring
from pyquery import PyQuery

from .model import Response
from .const import MUSLIMPRO_URL, GEOCODE_URL, AsrjuristicMethod, CalculationMethod


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
        self.session = session or ClientSession(loop=loop)

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

    async def search(self, location: str):
        geocode = await self.geocode(location=location)
        response = await self.session.get(MUSLIMPRO_URL, params=geocode, **self.request_kwargs)
        return self._slice(self, resp=await response.text()) if response.status == 200 else Exception(self._errors(response.status))
