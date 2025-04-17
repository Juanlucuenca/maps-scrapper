# API de Búsqueda de Restaurantes en Google Maps

Esta API permite buscar restaurantes en municipios de México con especialidad culinaria específica utilizando web scraping de Google Maps.

## Características

- Búsqueda de restaurantes por municipio y especialidad
- API REST con FastAPI
- Documentación automática con Swagger UI
- Opciones para limitar el número de resultados
- Extracción detallada de información de restaurantes:
  - Nombre, dirección, sitio web, teléfono
  - Número de reseñas y calificación promedio
  - Servicios disponibles: entrega, recogida, etc.
  - Horarios de apertura
  - Descripción del restaurante

## Requisitos del Sistema

- Python 3.8 - 3.12 (se recomienda 3.10 o 3.11)
  - **Nota importante**: Hay problemas conocidos con Python 3.13 en Windows
- Dependencias especificadas en `requirements.txt`

## Instalación

### Usando Python directamente

1. Clona este repositorio:
   ```
   git clone https://github.com/tu-usuario/google-maps-restaurant-api.git
   cd google-maps-restaurant-api
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Instala los navegadores necesarios para Playwright:
   ```
   playwright install chromium
   playwright install-deps chromium
   ```

4. Ejecuta la aplicación:
   ```
   uvicorn main:app --reload
   ```

### Usando Docker (recomendado)

1. Clona este repositorio y navega al directorio:
   ```
   git clone https://github.com/tu-usuario/google-maps-restaurant-api.git
   cd google-maps-restaurant-api
   ```

2. Construye y ejecuta con Docker Compose:
   ```
   docker-compose up -d
   ```

## Uso

Una vez que la aplicación esté en ejecución, puedes acceder a los siguientes endpoints:

- **Documentación de la API**: http://localhost:8000/docs
- **Endpoint de búsqueda (POST)**: http://localhost:8000/api/v1/buscar
- **Endpoint de búsqueda (GET)**: http://localhost:8000/api/v1/buscar?municipio=Cancun&especialidad=italiana

### Ejemplo de solicitud POST:

```json
{
  "municipio": "Cancun",
  "especialidad": "italiana",
  "limite": 5
}
```

### Ejemplo de respuesta:

```json
{
  "total_resultados": 5,
  "restaurantes": [
    {
      "nombre": "Restaurante Italiano",
      "direccion": "Av. Kukulcán 123, Zona Hotelera, Cancún",
      "sitio_web": "https://restauranteitaliano.com",
      "telefono": "+52 998 123 4567",
      "num_reviews": 456,
      "promedio_reviews": 4.7,
      "compras_en_tienda": "No",
      "recogida_en_tienda": "Yes",
      "entrega": "Yes",
      "tipo": "Restaurante italiano",
      "horario_apertura": "12:00–23:00",
      "introduccion": "Auténtica cocina italiana en Cancún con vistas al mar",
      "municipio": "Cancun"
    },
    ...
  ],
  "tiempo_ejecucion": 15.23
}
```

## Despliegue en DigitalOcean

### Utilizando App Platform

1. Sube el código a un repositorio Git (GitHub, GitLab, etc.)
2. Regístrate o inicia sesión en [DigitalOcean](https://www.digitalocean.com/)
3. Ve a App Platform y haz clic en "Create App"
4. Conecta tu repositorio Git
5. Selecciona la opción "Dockerfile" como tipo de componente
6. Configura recursos según tus necesidades
7. Despliega tu aplicación

### Utilizando Droplet

1. Crea un Droplet con la imagen de Docker en DigitalOcean
2. Conéctate al Droplet por SSH
3. Clona tu repositorio Git
4. Ejecuta la aplicación con Docker Compose:
   ```
   docker-compose up -d
   ```

## Solución de Problemas

### Error NotImplementedError en Windows con Python 3.13

Si ves el siguiente error:
```
NotImplementedError
```

Esto ocurre debido a incompatibilidades entre Playwright, asyncio y Python 3.13 en Windows. Soluciones:

1. **Recomendado**: Usa una versión anterior de Python (3.8-3.12)
2. **Alternativa**: Ejecuta la aplicación en Docker, que usa Linux

### Problemas con Playwright

Si tienes problemas con Playwright:

1. Verifica que los navegadores están instalados:
   ```
   playwright install
   ```

2. Instala las dependencias del sistema para Playwright:
   ```
   playwright install-deps
   ```

## Advertencias

- Este scraper puede ser bloqueado por Google si se utiliza de manera intensiva.
- No está diseñado para producción sin medidas adicionales (rotación de IPs, delays aleatorios, etc.)
- El uso excesivo puede violar los términos de servicio de Google.

## Licencia

[MIT](LICENSE)


# maps-scrapper
