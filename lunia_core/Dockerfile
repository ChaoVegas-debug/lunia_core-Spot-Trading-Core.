FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/app

WORKDIR /opt/app

COPY requirements/ requirements/
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements/base.txt

COPY . .

CMD ["python", "-m", "flask", "--app", "app.services.api.flask_app", "run", "--host=0.0.0.0", "--port=8000"]
