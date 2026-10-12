FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m appuser && mkdir -p /srv/runtime && chown -R appuser:appuser /srv
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
