FROM python:3.11-slim

# Evita prompts interactivos y prepara locale básico
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Crea usuario no-root
RUN useradd -m appuser

WORKDIR /app

# Dependencias del sistema mínimas (matplotlib necesita algunas librerías)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libfreetype6-dev libpng-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY app/ ./app/
# directorio para outputs
RUN mkdir -p /app/out && chown -R appuser:appuser /app
USER appuser
WORKDIR /app

# Por defecto: ejecución única del script
CMD ["python", "app/sendpulse_whatsapp_pull.py"]
