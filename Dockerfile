  
FROM python:3.9-buster
LABEL maintainer="Hecate#3523"

WORKDIR /NGC0000

COPY starter.py ./starter.py
COPY core.py ./core.py
COPY config.json ./config.json
COPY requirements.txt ./requirements.txt
COPY ./cogs ./cogs
COPY ./utilities ./utilities
COPY ./data ./data

RUN pip install -r requirements.txt

CMD ["python", "starter.py"]