from os import environ
from contextlib import asynccontextmanager

from aiohttp import ClientSession

from pydantic import BaseModel, Field

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis

import uvicorn

from MuslimProScrapper import Search, Response as MuslimProResp
from MuslimProScrapper.const import AsrjuristicMethod, CalculationMethod

@asynccontextmanager
async def lifespan(_):
    redis = aioredis.from_url(f"redis://:{environ.get('REDIS_PASS')}@redis")
    FastAPICache.init(RedisBackend(redis), prefix="muslimproapi-cache")
    yield

app = FastAPI(title='MuslimPro_API', lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


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
        res = await response.json()
        return f"{res['city']}, {res['regionName']}, {res['country']}, {res['continent']}"


class ModelResponse(BaseModel):
    location: str = Field(default="Location not found!!")
    calculationMethod: str = Field(default="")
    asrjuristicMethod: str = Field(default="")
    praytimes: dict = Field(default=dict())
    ramadhan: dict | str = Field(default="")


class BaseResponse(BaseModel):
    status_code: int = Field(default=200)
    message: str = Field(default="OK")
    data: ModelResponse = Field(default=ModelResponse())


@app.get('/favicon.ico')
def favicon() -> FileResponse:
    return FileResponse("static/favicon.ico")


@app.get('/', response_model=None)
async def get_location_based(request: Request) -> RedirectResponse | JSONResponse:
    resp: BaseResponse = BaseResponse()
    try:
        async with ClientSession() as session:
            client_ip: str = request.client.host
            location: str = await where_ip(session=session, ip_address=client_ip)

            redirect_url = request.url_for('main_app', **{'query': location})
            return RedirectResponse(redirect_url)

    except (IndexError, KeyError):
        resp.status_code = 404
        return JSONResponse(content=jsonable_encoder(resp), status_code=404)
    except:
        resp.message = "Something went wrong"
        resp.status_code = 500
        resp.data.location = ""
        return JSONResponse(content=jsonable_encoder(resp), status_code=500)


@app.get('/{query}', response_class=JSONResponse)
@cache(expire=86400)
async def main_app(query: str, calcMethod: str = "", asjurMethod: str = "") -> JSONResponse:
    resp: BaseResponse = BaseResponse()
    status: int = 200

    par1, par2 = calcMethod.replace(
        ' ', '_').upper(), asjurMethod.replace(' ', '_').upper()

    calc = CalculationMethod[par1] if hasattr(
        CalculationMethod, par1) else CalculationMethod.DEFAULT
    asjur = AsrjuristicMethod[par2] if hasattr(
        AsrjuristicMethod, par2) else AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI
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

                resp.data.location = f"{city_name.title()}, {country_name.title()}"
                resp.data.calculationMethod = data.calculationMethod
                resp.data.asrjuristicMethod = data.asrjuristicMethod
                for i in iter(data.raw):
                    resp.data.praytimes.update({
                        i.date: i.prayertimes
                    })

                if country_name.title() == "Indonesia":
                    resp.data.ramadhan = await api.ramadhan_time()
                else:
                    resp.data.ramadhan = "Currently only supported in Indonesia"

        except (IndexError, KeyError):
            status = 404
            resp.status_code = status
        except:
            status = 500
            resp.message = "Something went wrong"
            resp.status_code = status
            resp.data.location = ""

    return JSONResponse(content=jsonable_encoder(resp), status_code=status)


@app.exception_handler(400)
@app.exception_handler(404)
async def docs(e):
    return RedirectResponse('https://github.com/lleans/Muslim-Pro-Scrapper')

uvicorn.run("router:app", port=int(environ.get('PORT')) or 8000, workers=4)