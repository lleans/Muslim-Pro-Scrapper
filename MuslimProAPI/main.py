from aiohttp import ClientSession
from pyquery import PyQuery
from datetime import datetime, timedelta

from .model import Response
from .const import MUSLIMPRO_URL, GEOCODE_URL, AsrjuristicMethod, CalculationMethod, RAMADHAN_API_INDONESIA


class MuslimProException(Exception):

    def __init__(self, message: str = None, was_generic: bool = False, *, http_code: int) -> None:
        self.message = message
        self.http_code = http_code
        self.was_generic = was_generic

        super().__init__(self._errors())

    def _errors(self):
        if self.http_code:
            http_error: dict = {
                404: "Not found",
                302: "Moved temporarily, or blocked by captcha",
                403: "Forbidden,or unvalid",
                429:  "Too many request",
                500: "Server error",
            }

            return http_error.get(self.http_code, f"Unknown error, please report to the project maintainer. HTTP code {self.http_code}")
        elif self.was_generic:
            return self.message
        else:
            return f"Unknown error, please report to the project maintainer. {self.message}"


class Search:

    def __init__(self,
                 session=None,
                 *,
                 lib='asyncio',
                 loop=None,
                 calculation: CalculationMethod = CalculationMethod.DEFAULT,
                 asrjuristic: AsrjuristicMethod = AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI,
                 **request_kwargs
                 ) -> None:
        self.request_kwargs = request_kwargs
        self.calculation: CalculationMethod = calculation
        self.asrjuristic: AsrjuristicMethod = asrjuristic
        headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36"
        }

        if lib not in ('asyncio'):
            raise ValueError(
                f"lib must be of type `str` and be either `asyncio' not '{lib if isinstance(lib, str) else lib.__class__.__name__}'")
        self._lib = lib
        if lib == 'asyncio':
            from asyncio import get_event_loop
            loop = loop or get_event_loop()

        self.session = session or ClientSession(loop=loop, headers=headers)

    def _slice(self, resp: str) -> Response:
        data: PyQuery = PyQuery(resp)('tbody').eq(0)('tr')
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

    async def ramadhan_time(self):
        async with self.session.get(RAMADHAN_API_INDONESIA) as response:
            response = await response.text(encoding='utf-8')
            data = PyQuery(response).find('.content_wrapper tbody tr')

            res = {}
            for i in data.items():
                res.update(self._slice_ramadhan(i))

            return res

    async def geocode(self, location: str) -> dict:
        params: dict = {
            'query': location
        }

        async with self.session.get(GEOCODE_URL, params=params, **self.request_kwargs) as resp:
            if 200:
                data = await resp.json()
                return {
                    'country_code': data['data'][0]['country_module']['global']['alpha2'],
                    'country_name': data['data'][0]['country'],
                    'city_name': data['data'][0]['name'],
                    'coordinates': f"{data['data'][0]['latitude']},{data['data'][0]['longitude']}",
                    'convention': self.calculation.value,
                    'asrjuristic': self.asrjuristic.value
                }

            else:
                raise Exception(self._errors(resp.status))

    async def search(self, location: str) -> Response:
        geocode: dict = await self.geocode(location=location)
        async with self.session.get(MUSLIMPRO_URL, params=geocode, **self.request_kwargs) as resp:
            if resp.status != 200:
                raise Exception(self._errors(resp.status))

            resp = await resp.text(encoding='utf-8')
            return self._slice(resp=resp)
