FROM arm64v8/python:3.12.3-slim-bookworm
WORKDIR /app
COPY ./app.py .
RUN pip install aiohttp psutil
EXPOSE 8080
CMD ["python3", "./app.py"]
