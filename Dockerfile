FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias necesarias para Playwright y VNC
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
    x11vnc \
    fluxbox \
    xterm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar entorno VNC
RUN mkdir -p ~/.vnc && \
    echo "#!/bin/sh\nfluxbox &" > ~/.vnc/xstartup && \
    chmod +x ~/.vnc/xstartup

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

# Configurar script de inicio con soporte VNC
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Puerto expuesto para la API y VNC
EXPOSE 8000 5900

# Comando para ejecutar la aplicación con VNC
CMD ["/start.sh"] 