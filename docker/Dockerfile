FROM python:3.10-slim-buster

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV EVENT_PORT=50060

EXPOSE 50060

CMD ["python3", "-u", "src/main.py"]
