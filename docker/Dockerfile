FROM python:3.10-slim-buster

RUN apt-get update && apt-get install -y \
    git pkg-config python3-dev default-libmysqlclient-dev build-essential && \
    git clone https://github.com/OpenSIPS/opensips-cli.git /src/opensips-cli && \
    cd /src/opensips-cli && \
    python3 setup.py install clean

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 50060

CMD ["python3", "-u", "src/main.py"]
