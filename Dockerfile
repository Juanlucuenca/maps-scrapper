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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar playwright y navegadores
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Copiar el código de la aplicación
COPY . .

# Puerto expuesto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["python", "main.py"] 