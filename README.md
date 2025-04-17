# Google Maps Scraper API

API para extraer información de restaurantes y lugares desde Google Maps.

## Requisitos

- Docker y Docker Compose instalados en el servidor
- Un Droplet de Digital Ocean (recomendado: Ubuntu 22.04)
- Al menos 2GB de RAM para ejecutar el servicio

## Estructura del Proyecto

```
.
├── main.py           # Código principal de la API
├── Dockerfile        # Configuración para construir la imagen Docker
├── docker-compose.yml # Configuración para orquestar servicios Docker
├── requirements.txt  # Dependencias de Python
└── README.md         # Este archivo
```

## Despliegue en Digital Ocean

### 1. Crear un Droplet en Digital Ocean

1. Inicia sesión en tu cuenta de Digital Ocean
2. Crea un nuevo Droplet con las siguientes especificaciones:
   - Ubuntu 22.04 (LTS) x64
   - Plan Básico con al menos 2GB RAM / 1 CPU
   - Agrega tu clave SSH o configura una contraseña

### 2. Configurar el Servidor

Una vez creado el Droplet, conéctate a él via SSH:

```bash
ssh root@TU_IP_DEL_DROPLET
```

Actualiza el sistema e instala Docker y Docker Compose:

```bash
# Actualizar paquetes
apt update && apt upgrade -y

# Instalar dependencias
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Agregar clave GPG de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Agregar repositorio de Docker
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Actualizar e instalar Docker
apt update
apt install -y docker-ce

# Instalar Docker Compose
mkdir -p ~/.docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/download/v2.16.0/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose

# Verificar instalación
docker --version
docker compose version
```

### 3. Clonar y Desplegar el Proyecto

```bash
# Crear directorio para el proyecto
mkdir -p /opt/maps-scraper
cd /opt/maps-scraper

# Copiar archivos del proyecto
# (puedes usar SCP, Git, o copiar y pegar manualmente)

# Construir y levantar los contenedores
docker compose up -d --build

# Verificar que el contenedor está funcionando
docker ps
```

### 4. Probar la API

Una vez que el servicio esté en funcionamiento, puedes probar la API:

```bash
# Verificar que el servicio responde
curl http://localhost:8000/

# Realizar una búsqueda (reemplaza con tu propia solicitud)
curl -X POST http://localhost:8000/search-google-maps \
  -H "Content-Type: application/json" \
  -d '{"municipality":"CDMX","especiality":"Japones","limit":5}'
```

### 5. Configuración de Firewall (Opcional)

Para exponer el servicio de forma segura:

```bash
# Instalar y configurar UFW (Uncomplicated Firewall)
apt install -y ufw
ufw allow ssh
ufw allow 8000/tcp
ufw enable

# Verificar reglas
ufw status
```

## Uso de la API

### Endpoints Disponibles

- `GET /`: Health check
- `POST /search-google-maps`: Buscar restaurantes en Google Maps

### Ejemplo de Solicitud

```json
{
  "municipality": "CDMX",
  "especiality": "Japones",
  "limit": 5
}
```

### Ejemplo de Respuesta

```json
{
  "items": [
    {
      "name": "Nombre del Restaurante",
      "addresse": "Dirección completa",
      "website": "https://sitio-web.com",
      "phone_number": "+52 55 1234 5678",
      "schedule": "lunes: 1–11 p.m., martes: 1–11 p.m., ..."
    },
    ...
  ]
}
```

## Mantenimiento

### Ver Logs del Contenedor

```bash
docker logs maps-scraper
```

### Reiniciar el Servicio

```bash
cd /opt/maps-scraper
docker compose restart
```

### Actualizar el Servicio

```bash
cd /opt/maps-scraper
# Actualiza los archivos necesarios
docker compose down
docker compose up -d --build
```


