from aiohttp import ClientSession
from MuslimProAPI import Search
from flask import Flask, jsonify, redirect, abort, request
from os import environ

from MuslimProAPI.const import AsrjuristicMethod, CalculationMethod

app = Flask('MuslimPro_API')

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSON_SORT_KEYS'] = False

@app.route('/<string:query>', methods=['GET'])
async def main_app(query: str):
    response = {}
    query = query.strip()
    if query != "":
        par1, par2 = str(request.args.get('calcMethod')).replace(' ', '_').upper(), str(request.args.get('asjurMethod')).replace(' ', '_').upper()
        calcMethod = CalculationMethod[par1].value if hasattr(CalculationMethod, par1) else CalculationMethod.DEFAULT.value
        asrjurMethod = AsrjuristicMethod[par2].value if hasattr(AsrjuristicMethod, par2) else AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI.value
        async with ClientSession() as session:
            api = Search(session=session, calculation=calcMethod, asrjuristic=asrjurMethod)
            data = await api.search(location=query)
            session.close()

        response['location'] = query.title()
        response['calculationMethod'] = data.calculationMethod
        response['asrjuristicMethod'] = data.asrjuristicMethod
        response['praytimes'] = {}
        for i in iter(data.raw):
            response['praytimes'][i.date] = i.prayertimes
        
        return jsonify(response)
    else:
        abort(400)

@app.errorhandler(400)
@app.errorhandler(404)
async def docs(e):
    return redirect('https://github.com/lleans/Muslim-Pro-Scrapper')

app.run(port=environ.get('PORT') or 8000, host='0.0.0.0', threaded=False)
