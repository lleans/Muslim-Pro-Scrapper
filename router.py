from aiohttp import ClientSession
from flask import Flask, jsonify, redirect, request, url_for
from flask_caching import Cache
from os import environ

from MuslimProScrapper import Search
from MuslimProScrapper.const import AsrjuristicMethod, CalculationMethod

config: dict = {
    'CORS_HEADERS': 'Content-Type',
    'JSON_SORT_KEYS': False,
    'CACHE_TYPE': 'FileSystemCache',
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_DIR": "cache"
}

app = Flask('MuslimPro_API')
app.config.from_mapping(config)
cache: Cache = Cache(app)


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


@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='favicon.ico')


@app.route('/<string:query>', methods=['GET'])
@app.route('/', methods=['GET'])
@cache.cached(query_string=True)
async def main_app(query: str = None):
    not_found = 'Location not Found'
    response = {
        'location': "",
        'calculationMethod': "",
        'asrjuristicMethod': "",
        'praytimes': "",
        'ramadhan': ""
    }

    par1, par2 = str(request.args.get('calcMethod')).replace(' ', '_').upper(), str(
        request.args.get('asjurMethod')).replace(' ', '_').upper()
    calcMethod = CalculationMethod[par1] if hasattr(
        CalculationMethod, par1) else CalculationMethod.DEFAULT
    asrjurMethod = AsrjuristicMethod[par2] if hasattr(
        AsrjuristicMethod, par2) else AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI
    async with ClientSession() as session:
        api = Search(session=session, calculation=calcMethod,
                     asrjuristic=asrjurMethod)
        try:
            if query is None:
                list_ip = request.headers['x-forwarded-for'].split(',')
                query = await where_ip(session=session, ip_address=list_ip[len(list_ip)-1] or request.remote_addr)
            else:
                query = query.strip()
            data = await api.search(location=query)
            location = await api.geocode(location=query)

            if location['country_name'].title() == "Indonesia":
                response['ramadhan'] = await api.ramadhan_time()
            else:
                response['ramadhan'] = "Currently only supported in Indonesian"
        except (IndexError, KeyError):
            response['location'] = not_found

    if response['location'] != not_found:
        response['location'] = f"{location['city_name'].title()}, {location['country_name'].title()}"
        response['calculationMethod'] = data.calculationMethod
        response['asrjuristicMethod'] = data.asrjuristicMethod
        response['praytimes'] = {}
        for i in iter(data.raw):
            response['praytimes'][i.date] = i.prayertimes

    return jsonify(response)


@app.errorhandler(400)
@app.errorhandler(404)
async def docs(e):
    return redirect('https://github.com/lleans/Muslim-Pro-Scrapper')

app.run(port=environ.get('PORT') or 8000, host='0.0.0.0', threaded=False)
