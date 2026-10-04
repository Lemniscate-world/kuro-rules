# kuro-dashboard (Docker) — API + web UI, zero daemon requis.
FROM python:3.12-slim
RUN pip install --no-cache-dir psutil
COPY src /app/src
WORKDIR /app
ENV PYTHONPATH=/app/src
EXPOSE 8767
# API seule ecoute 127.0.0.1 : publier le port pour voir depuis l hote.
# allow-no-db : aucune base dans l image, /api/system repond quand meme.
CMD ["python", "-m", "kuro_dashboard", "--host", "0.0.0.0", "--port", "8767", "--allow-no-db"]
