FROM python:3.13-slim
LABEL maintainer="ilchuk.cergey@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/media
RUN mkdir -p /app/static

RUN adduser \
    --disabled-password \
    --no-create-home \
    django_user

RUN chown -R django_user /app/media
RUN chmod -R 755 /app/media
RUN chown -R django_user /app/static
RUN chmod -R 755 /app/static

EXPOSE 8000

USER django_user
