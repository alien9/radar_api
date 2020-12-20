# radar_api
Radar API

Pré-Requisitos

Debian 10 (buster)
nginx web server
docker-compose

Configurações

arquivo .env

HOSTNAME=localhost
HOST_URL=http://localhost
DJANGO_ENV=development
DRIVER_DB_HOST=localhost
DRIVER_DB_NAME=radartona1
DRIVER_DB_PASSWORD=driver
STATIC_ROOT=/var/www/static/
STATIC_URL=http://localhost/radarapi/
DAILY_QUOTA=6/minute



