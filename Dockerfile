FROM python:3.8-buster

RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends libgdal-dev

RUN apt-get update && apt-get install -y \    
    gettext \
    libgeos-dev \
    libspatialindex-dev \
    gdal-bin \
    memcached

RUN ["gdal-config", "--version"]

RUN mkdir -p /opt/app
WORKDIR /opt/app

COPY . /opt/app

RUN pip install --no-cache-dir gunicorn
RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "radar.wsgi", "-w3", "-b:4000", "-kgevent"]
