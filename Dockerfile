FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Copiar y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Instalar navegadores de Playwright y eliminar la necesidad de la ruta específica
RUN playwright install chromium
RUN playwright install-deps chromium

# Exponer puerto para FastAPI
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 