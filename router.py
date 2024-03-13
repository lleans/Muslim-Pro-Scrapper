from os import environ
from contextlib import asynccontextmanager

from aiohttp import ClientSession

from pydantic import BaseModel, Field

from fastapi import FastAPI, Request, HTTPException
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
    redis = aioredis.from_url("redis://redis")
    FastAPICache.init(RedisBackend(redis), prefix="muslimproapi-cache")
    yield

app = FastAPI(title='MuslimPro API', lifespan=lifespan, version="2.0")
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
    location: str = Field(default="")
    calculationMethod: str = Field(default="")
    asrjuristicMethod: str = Field(default="")
    praytimes: dict = Field(default=dict())
    ramadhan: dict | str = Field(default="")


class BaseResponse(BaseModel):
    status_code: int = Field(default=200)
    message: str = Field(default="OK")
    data: ModelResponse = Field(default=ModelResponse())


class CustomException(Exception):

    def __init__(self, status_code: int, message: str) -> None:
        self.body: BaseResponse = BaseResponse()
        self.body.status_code = status_code
        self.body.message = message
        self.body.data.location = ""


@app.get('/favicon.ico', response_class=FileResponse, include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse("static/favicon.ico")


@app.get('/', response_class=RedirectResponse, responses={
    307: {'description': "Will redirect into your specific location path"}
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

    except (IndexError, KeyError):
        raise CustomException(
            status_code=404, message="Location was not found!!")
    except:
        raise CustomException(
            status_code=500, message="Something went wrong!?")


@app.get('/{query}', response_model=BaseResponse, responses={
    200: {'description': "Will return the data, as the model", 'model': BaseResponse}
})
@cache(expire=86400)
async def main_app(query: str, calcMethod: str = CalculationMethod.DEFAULT.name, asjurMethod: str = AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI.name) -> JSONResponse:
    """
    Main Appplication

    -   Query\n
        :query -> Pass this your location, to lookup the data
    -   Parameters\n
        :calcMethod[Optional] -> Put calculation method(read source code)\n
        :asjurMethod[Optional] -> Put asrjuristic method(read source code)
    """
    resp: BaseResponse = BaseResponse()

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
                    resp.data.ramadhan = "Currently only supported in Indonesia"

        except (IndexError, KeyError):
            raise CustomException(
                status_code=404, message="Location was not found!!")
        except:
            raise CustomException(
                status_code=500, message="Something went wrong!?")

    return JSONResponse(content=jsonable_encoder(resp))


@app.exception_handler(404)
@app.exception_handler(500)
@app.exception_handler(422)
@app.exception_handler(400)
async def error_handling(_, exec: Exception) -> JSONResponse:
    if isinstance(exec, CustomException):
        return JSONResponse(content=jsonable_encoder(exec.body), status_code=exec.body.status_code)

    return RedirectResponse(url='/docs')

if __name__ == "__main__":
    uvicorn.run("router:app", host="0.0.0.0",
                port=int(environ.get('PORT')) or 8000, log_level="info", workers=3, forwarded_allow_ips="*")
