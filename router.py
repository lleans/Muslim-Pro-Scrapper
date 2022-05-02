from aiohttp import ClientSession
from MuslimProAPI import Search
from flask import Flask, jsonify, redirect, abort
from os import environ

app = Flask('MuslimPro_API')

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSON_SORT_KEYS'] = False

@app.route('/<string:query>', methods=['GET'])
async def main_app(query: str):
    response = {}
    query = query.strip()
    if query != "":
        async with ClientSession() as session:
            api = Search(session=session)
            data = await api.search(location=query)
        
        response['location'] = query.capitalize()
        response['date'] = "Today"
        response['praytimes'] = {}
        for i in range(6):
            response['praytimes'][data.raw[i].prayers] = data.raw[i].praytime
        
        return jsonify(response)
    else:
        abort(400)

@app.errorhandler(400)
@app.errorhandler(404)
async def docs(e):
    return redirect('https://github.com/lleans/Muslim-Pro-Scrapper')

app.run(port=environ.get('PORT') or 8000, host='0.0.0.0')
