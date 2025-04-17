FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias necesarias para Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libnspr4 \
    libnss3 \
    fonts-liberation \
    libcurl4 \
    libdbus-1-3 \
    xvfb \
    # Dependencias adicionales para navegadores headless en servidores
    ca-certificates \
    fonts-noto-color-emoji \
    ttf-dejavu \
    ttf-liberation \
    locales \
    # Herramientas para diagnóstico
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar locale
RUN locale-gen es_ES.UTF-8
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES:es
ENV LC_ALL es_ES.UTF-8

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar playwright y navegadores con verificación
RUN pip install playwright==1.40.0 && \
    playwright install chromium && \
    playwright install-deps chromium && \
    # Verificar que Playwright está instalado correctamente
    python -c "from playwright.sync_api import sync_playwright; print('Playwright instalado correctamente')"

# Crear directorios para logs y screenshots
RUN mkdir -p /app/logs /app/screenshots

# Copiar el código de la aplicación
COPY . .

# Puerto expuesto
EXPOSE 8000

# Establecer variables de entorno
ENV HEADLESS=true
ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["python", "main.py"] 