FROM arm64v8/python:3.12.3-alpine3.19

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY ./server.py .

CMD ["python3", "./server.py"]