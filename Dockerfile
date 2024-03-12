FROM python:3.12-slim

COPY . /app
WORKDIR /app
RUN pip3 install -Ur requirements.txt

CMD ["gunicorn"  , "router:app", "-w 4", "-k uvicorn.workers.UvicornWorker"]