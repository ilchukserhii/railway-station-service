# Railway Station API

API service for searching railway tickets and managing railway station infrastructure written with Django REST Framework

## Installation

Install PostgreSQL and create database

```bash
git clone https://github.com/ilchukserhii/railway-station-service.git
cd railway-station-service

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
```

Fill variables in `.env` file

```bash
python manage.py migrate
python manage.py runserver
```

Load demo data:
```bash
python manage.py loaddata data.json
```

## Run with docker

Docker should be installed

```bash
cp .env.sample .env
docker compose build
docker compose up
```
Load demo data
```bash
docker compose exec app python manage.py loaddata data.json
```

## Getting access

Admin user:
 - admin@admin.com
 - Strongpass12345


## Features

- JWT authentication
- Admin panel /admin/
- Swagger documentation available at /api/docs/
- OpenAPI schema available at /api/schema/
- View trips (available for any user)
- Filtering trips by multiple filters like route, departure or arrival time, etc.
- Managing orders and tickets
- Administrate railway infrastructure like creating/updating/deleting routes, trains, crews, etc.
- Docker support
- PostgreSQL support
- Upload images for trains and crew members
