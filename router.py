from os import environ
from typing import Annotated
from contextlib import asynccontextmanager

from aiohttp import ClientSession

from pydantic import BaseModel, Field

from fastapi import FastAPI, Request, Query, Path
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis

import uvicorn

from MuslimProScrapper import Search, Response as MuslimProResp
from MuslimProScrapper.const import AsrjuristicMethod, CalculationMethod


@asynccontextmanager
async def lifespan(_):
    redis = aioredis.from_url("redis://redis")
    FastAPICache.init(RedisBackend(redis), prefix="muslimproapi-cache")
    yield

description: str = """
# Muslim Pro Scrapper 🕌
Simple scrapper using aiohttp and pyquery to get Praytime for moslem people

## Calculation Option 🕹
You can see the option by importing class with name ```CalculationMethod``` and ```AsrjuristicMethod```, same with the api request you need to pass **The Variable Name on Const Class** on params ```calcMethod``` ```asrjurMethod```, here the list of it

```python
class CalculationMethod(Enum):
    DEFAULT = "Precalc"
    ALGERIAN_MINISTER_OF_RELIGIOUS_AND_WAKFS = "Algeria"
    DIYANET_İŞLERI_BAŞKANLIĞI = "Diyanet"
    EGYPTIAN_GENERAL_AUTHORITY = "Egypt"
    EGYPTIAN_GENERAL_AUTHORITY_BIS = "EgyptBis"
    FIXED_ISHA_ANGLE_INTERVAL = "FixedIsha"
    FRANCE_UOIF_ANGLE_12DEG = "UOIF"
    FRANCE_ANGLE_15DEG = "Fr15"
    FRANCE_ANGLE_18DEG = "Fr18"
    ISLAMIC_UNIVERSITY_KARACHI = "Karachi"
    JAKIM_JABATAN_KEMAJUAN_ISLAM_MALAYSIA = "JAKIM"
    LONDON_UNIFIED_ISLAMIC_PRAYER_TIMETABLE = "UIPTL"
    MUIS_MAJLIS_UGAMA_ISLAM_SINGAPURA = "MUIS"
    MUSLIM_WORLD_LEAGUE_MWL = "MWL"
    NORTH_AMERICA_ISNA = "ISNA"
    SHIA_ITHNA_ASHARI_JAFARI = "Jafari"
    SIHAT_KEMENAG_KEMENTERIAN_AGAMA_RI = "KEMENAG"
    TUNISIAN_MINISTRY_OF_RELIGIOUS_AFFAIRS = "Tunisia"
    UAE_GENERAL_AUTHORITY_OF_ISLAMIC_AFFAIRS_AND_ENDOWMENTS = "AwqafUAE"
    UMM_AL_QURA_MAKKAH = "Makkah"
    UNIVERSITY_OF_TEHRAN = "Tehran"
    FEDERATION_OF_ISLAMIC_ASSOCIATIONS_IN_BASQUE_COUNTRY = "BASQUE"


class AsrjuristicMethod(Enum):
    STANDARD_SHAFI_MALIKI_HANBALI = "Standard"
    HANAFI = "Hanafi"
```

Here some reference for calculation method<br />
- [Prayer Time Calculation - PrayTimes.org 📚](http://praytimes.org/calculation)
- [California IslamiC University 🎓](https://www.calislamic.com/fifteen-or-eighteen-degrees-calculating-prayer-and-fasting-times-in-islam/)
"""

app = FastAPI(
    title='MuslimPro API',
    lifespan=lifespan,
    version="2.0",
    description=description,
    summary="MuslimPro Scrapper cache based API 🕌",
    license_info={
        "name": "MIT License",
        "url": "https://github.com/lleans/Muslim-Pro-Scrapper/raw/main/LICENSE",
    })


async def where_ip(session: ClientSession, ip_address: str) -> str:
    url = "https://demo.ip-api.com/json/"
    headers = {
        "Origin": "https://ip-api.com",
        "Referer": "https://ip-api.com",
        "Host": "demo.ip-api.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    params = {
        "fields": environ.get("API_KEY") or open("API_KEY").readline(),
        "lang": "en"
    }
    async with session.get(url+ip_address, params=params, headers=headers) as response:
        res: dict = await response.json()
        return f"{res['city']}, {res['regionName']}, {res['country']}, {res['continent']}"


class ModelResponse(BaseModel):
    location: str = Field()
    calculationMethod: str = Field()
    asrjuristicMethod: str = Field()
    praytimes: dict = Field()
    ramadhan: dict | None = Field()


class BaseResponse(BaseModel):
    status: int = Field()
    message: str = Field()
    data: ModelResponse | None = Field()


class CustomException(Exception):

    def __init__(self, status: int, message: str) -> None:
        self.status: int = status
        self.message: str = message


@app.get('/', response_class=RedirectResponse, responses={
    307: {'description': "Will redirect into your specific location path", 'content': {
        'application/text': {
            'example': "Redirect to specific path based your location"
        }
    }},
    404: {'description': "Will return when location is not found", 'model': BaseResponse,
          'content': {
              'application/json': {
                  'example': {
                      'status': 404,
                      'message': "Location was not found!!",
                      'data': "null"
                  }
              }
          }},
})
async def get_location_based(request: Request) -> RedirectResponse:
    """
    Root redirection based ip

    By Looking up your ip adress location, this will redirect you into the specific path based your location
    """
    try:
        async with ClientSession() as session:
            client_ip: str = request.client.host
            location: str = await where_ip(session=session, ip_address=client_ip)

            redirect_url = request.url_for('main_app', **{'query': location})
            return RedirectResponse(redirect_url)

    except KeyError:
        raise CustomException(
            status=404, message="Location was not found!!")


@app.get('/{query}', response_model=BaseResponse, responses={
    200: {'description': "Will return the data, as the model", 'model': BaseResponse,
          'content': {
              'application/json': {
                  'example': {
                      "status_code": 200,
                      "message": "OK",
                      "data": {
                          "location": "Jakarta, Indonesia",
                          "calculationMethod": "DEFAULT",
                          "asrjuristicMethod": "STANDARD_SHAFI_MALIKI_HANBALI",
                          "praytimes": {
                              "Fri 1 Mar": {
                                  "Fajr": "04:42",
                                  "Sunrise": "05:56",
                                  "Dhuhr": "12:08",
                                  "Asr": "15:10",
                                  "Maghrib": "18:14",
                                  "Isha'a": "19:23"
                              },
                              "Sat 2 Mar": {
                                  "Fajr": "04:42",
                                  "Sunrise": "05:56",
                                  "Dhuhr": "12:08",
                                  "Asr": "15:09",
                                  "Maghrib": "18:13",
                                  "Isha'a": "19:23"
                              },
                              "next": {
                                  "key": "value"
                              }
                          },
                          "ramadhan": {
                              "2010": {
                                  "start": "August 11",
                                  "end": "September 10"
                              },
                              "2011": {
                                  "start": "August 01",
                                  "end": "August 31"
                              },
                              "next": {
                                  "key": "value"
                              }
                          }
                      }
                  }
              }
          }},
    404: {'description': "Will return when location is not found", 'model': BaseResponse,
          'content': {
              'application/json': {
                  'example': {
                      "status_code": 404,
                      "message": "Location was not found!!",
                      "data": "null"
                  }
              }
          }},
    422: {'description': "Will return when peforming bad request", 'model': BaseResponse,
          'content': {
              'application/json': {
                  'example': {
                      "status_code": 422,
                      "message": "Bad request, please check your datatypes or make sure to fill all parameter",
                      "data": "null"
                  }
              }
          }},
    400: {'description': "Will return when peforming bad request", 'model': BaseResponse,
          'content': {
              'application/json': {
                  'example': {
                      "status_code": 422,
                      "message": "Bad request, please check your datatypes or make sure to fill all parameter",
                      "data": "null"
                  }
              }
          }}
})
@cache(expire=86400)
async def main_app(
        query: Annotated[str, Path(
            title="Location query", description="Pass your city/country name")],
        calcMethod: Annotated[str, Query(title="Calculation method params", description="Read the docs description for more info(CalculationMethod)",
                                         pattern="^[a-zA-Z_]+$")] = CalculationMethod.DEFAULT.name,
        asjurMethod: Annotated[str, Query(title="Asrjuristic method params", description="Read the docs description for more info(AsrjuristicMethod)", pattern="^[a-zA-Z_]+$")] = AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI.name) -> JSONResponse:
    """
    Main Appplication

    -   Query\n
        ```:query``` Pass this your location, to lookup the data
    -   Parameters\n
        ```:calcMethod[Optional]``` Put calculation method(read ```CalculationMethod```)\n
        ```:asjurMethod[Optional]``` Put asrjuristic method(read ```AsrjuristicMethod```)

    **for ramadhan, currently only work in Indonesia city's**
    """
    resp: BaseResponse = BaseResponse(status=200, message="OK",
                                      data=ModelResponse(
                                          location=query.capitalize(), calculationMethod="", asrjuristicMethod="", praytimes={}, ramadhan={})
                                      )

    par1 = calcMethod.replace(' ', '_').upper()
    par2 = asjurMethod.replace(' ', '_').upper()
    calc = CalculationMethod[par1]
    asjur = AsrjuristicMethod[par2]

    async with ClientSession() as session:
        api = Search(session=session, calculation=calc,
                     asrjuristic=asjur)
        try:
            query = query.strip()

            data: MuslimProResp = await api.search(location=query)
            location: dict = await api.geocode(location=query)

            if location:
                city_name: str = location.get('city_name', '')
                country_name: str = location.get('country_name', '')

                resp.data.location = f"{city_name.title()}, {
                    country_name.title()}"
                resp.data.calculationMethod = data.calculationMethod
                resp.data.asrjuristicMethod = data.asrjuristicMethod
                for i in iter(data.raw):
                    resp.data.praytimes.update({
                        i.date: i.prayertimes
                    })

                if country_name.title() == "Indonesia":
                    resp.data.ramadhan = await api.ramadhan_time()
                else:
                    resp.data.ramadhan = None

        except (KeyError, IndexError):
            raise CustomException(
                status=404, message="Location was not found!!")

    return JSONResponse(content=jsonable_encoder(resp))


@app.exception_handler(RequestValidationError)
async def validation_handling(_, __) -> JSONResponse:
    resp: BaseResponse = BaseResponse(
        status=400, message="Bad request, please check your datatypes or make sure to fill all parameter", data=None)
    return JSONResponse(content=jsonable_encoder(resp), status_code=resp.status)


@app.exception_handler(404)
async def error_handling_lf(_, __) -> RedirectResponse:
    return RedirectResponse(url='/docs')


@app.exception_handler(500)
@app.exception_handler(CustomException)
async def error_handling(_, exec: Exception) -> JSONResponse:
    resp: BaseResponse = BaseResponse(
        status=500, message="Something went wrong!! " + str(exec), data=None)

    if isinstance(exec, CustomException):
        resp.status = exec.status or 500
        resp.message = exec.message or str(exec)

    return JSONResponse(content=jsonable_encoder(resp), status_code=resp.status)

if __name__ == "__main__":
    uvicorn.run("router:app", host="0.0.0.0",
                port=int(environ.get('PORT')) or 8000, log_level="info", forwarded_allow_ips="*")
