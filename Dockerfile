FROM python:3.13-slim

WORKDIR /app

ENV FLASK_APP=app.py

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "flask db upgrade && gunicorn -b 0.0.0.0:${PORT:-8080} app:app"]
