from aiohttp import ClientSession
from MuslimProAPI import Search
from flask import Flask, jsonify, redirect, request
from os import environ

from MuslimProAPI.const import AsrjuristicMethod, CalculationMethod

app = Flask('MuslimPro_API')

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSON_SORT_KEYS'] = False

async def where_ip(session, ip_address: str):
    url = "https://demo.ip-api.com/json/"
    headers = {
        "Origin": "https://ip-api.com",
        "Referer": "https://ip-api.com"
    }
    params = {
        "fields": environ.get("API_KEY") or open("API_KEY").readline(),
        "lang": "en"
    }
    response = await session.get(url+ip_address, params=params, headers=headers)
    response = await response.json()
    return f"{response['city']}, {response['regionName']}, {response['country']}, {response['continent']}"

@app.route('/<string:query>', methods=['GET'])
@app.route('/', methods=['GET'])
async def main_app(query: str = None):
    not_found = 'Location not Found'
    response = {
        'location': "",
        'calculationMethod': "",
        'asrjuristicMethod': "",
        'praytimes': "",
        'ramadhan': ""
    }

    par1, par2 = str(request.args.get('calcMethod')).replace(' ', '_').upper(), str(request.args.get('asjurMethod')).replace(' ', '_').upper()
    calcMethod = CalculationMethod[par1].value if hasattr(CalculationMethod, par1) else CalculationMethod.DEFAULT.value
    asrjurMethod = AsrjuristicMethod[par2].value if hasattr(AsrjuristicMethod, par2) else AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI.value
    async with ClientSession() as session:
        api = Search(session=session, calculation=calcMethod, asrjuristic=asrjurMethod)
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
        session.close()

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