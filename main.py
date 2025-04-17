from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright
import pandas as pd
import re
import os
import time
import logging
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
import uvicorn
import asyncio
import platform
import sys

# Configuración especial para Windows con Python 3.13+
if platform.system() == 'Windows' and sys.version_info >= (3, 13):
    # Para evitar el NotImplementedError en Windows con Python 3.13+
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Crear directorio de logs si no existe
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title="Google Maps Restaurant Scraper API",
    description="API para buscar restaurantes en municipios de México con especialidades específicas",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
class SearchRequest(BaseModel):
    municipio: str
    especialidad: Optional[str] = None
    limite: Optional[int] = None

class RestaurantData(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    sitio_web: Optional[str] = None
    telefono: Optional[str] = None
    num_reviews: Optional[int] = 0
    promedio_reviews: Optional[float] = 0.0
    compras_en_tienda: Optional[str] = None
    recogida_en_tienda: Optional[str] = None
    entrega: Optional[str] = None
    tipo: Optional[str] = None
    horario_apertura: Optional[str] = None
    introduccion: Optional[str] = None
    municipio: str

class SearchResponse(BaseModel):
    total_resultados: int
    restaurantes: List[RestaurantData]
    tiempo_ejecucion: float

# Función auxiliar para extraer datos usando XPath
async def extract_data(xpath, page):
    if await page.locator(xpath).count() > 0:
        return await page.locator(xpath).inner_text()
    return ""

# Función principal para buscar restaurantes (ahora asíncrona)
async def buscar_restaurantes(municipio: str, especialidad: Optional[str] = None, limite: Optional[int] = None) -> Dict[str, Any]:
    tiempo_inicio = time.time()
    
    logger.info(f"Iniciando búsqueda de restaurantes en: {municipio}")
    if especialidad:
        logger.info(f"Especialidad: {especialidad}")
    
    # Construir el término de búsqueda
    if especialidad:
        search_term = f"restaurantes {especialidad} en {municipio} México"
    else:
        search_term = f"restaurantes en {municipio} México"
    
    logger.info(f"Término de búsqueda: {search_term}")
    
    # Inicializar listas para almacenar datos
    restaurantes = []
    
    try:
        # Manejo especial para evitar errores en diferentes sistemas
        try:
            async with async_playwright() as p:
                # Configurar el navegador (headless=True para producción)
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Abrir Google Maps y realizar la búsqueda
                logger.info("Navegando a Google Maps")
                await page.goto("https://www.google.com/maps/@32.9817464,70.1930781,3.67z?", timeout=60000)
                await page.wait_for_timeout(2000)

                logger.info(f"Realizando búsqueda: {search_term}")
                await page.locator('//input[@id="searchboxinput"]').fill(search_term)
                await page.keyboard.press("Enter")
                await page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]')
                
                await page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
                
                # Lógica de scroll para cargar resultados
                logger.info("Cargando resultados...")
                previously_counted = 0
                scroll_attempts = 0
                max_scroll_attempts = 20  # Reducido para la API
                no_new_results_count = 0
                
                while scroll_attempts < max_scroll_attempts:
                    # Hacer múltiples scrolls para cargar más resultados
                    for _ in range(3):
                        await page.mouse.wheel(0, 30000)
                        await page.wait_for_timeout(2000)
                    
                    # Esperar a que los resultados se carguen
                    try:
                        await page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=5000)
                        await page.wait_for_timeout(1000)
                    except Exception:
                        logger.warning("Error esperando selectores. Continuando...")
                    
                    try:
                        current_count = await page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                        logger.info(f"Resultados encontrados hasta ahora: {current_count}")
                        
                        # Si se especificó un límite y ya lo alcanzamos, terminamos
                        if limite is not None and current_count >= limite:
                            logger.info(f"Se alcanzó el límite solicitado ({limite})")
                            listings = await page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                            listings = listings[:limite]
                            listings = [listing.locator("xpath=..") for listing in listings]
                            break
                        
                        # Si no hay cambios en 2 intentos, consideramos que ya se cargaron todos los resultados
                        if current_count == previously_counted:
                            no_new_results_count += 1
                            
                            if no_new_results_count >= 2:
                                logger.info(f"No se encontraron más resultados después de 2 intentos.")
                                listings = await page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                                listings = [listing.locator("xpath=..") for listing in listings]
                                break
                            
                            # Intentar un desplazamiento más agresivo
                            await page.mouse.wheel(0, 50000)
                            await page.wait_for_timeout(3000)
                        else:
                            # Reiniciar el contador si encontramos nuevos resultados
                            no_new_results_count = 0
                            previously_counted = current_count
                    except Exception as e:
                        logger.error(f"Error contando resultados: {str(e)}")
                        scroll_attempts += 1
                        continue
                    
                    scroll_attempts += 1
                
                # Si llegamos al máximo de intentos o no hay resultados
                if scroll_attempts >= max_scroll_attempts:
                    logger.info(f"Se alcanzó el máximo de intentos de scroll ({max_scroll_attempts})")
                    listings = await page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                    listings = [listing.locator("xpath=..") for listing in listings]
                
                if not listings:
                    logger.warning(f"No se encontraron resultados para la búsqueda: {search_term}")
                    return {
                        "total_resultados": 0,
                        "restaurantes": [],
                        "tiempo_ejecucion": time.time() - tiempo_inicio
                    }
                
                total_listings = len(listings)
                logger.info(f"Total de lugares encontrados: {total_listings}")
                
                # Limitar el número de resultados a procesar si se especificó
                if limite is not None and limite < total_listings:
                    total_listings = limite
                    listings = listings[:limite]
                
                # Procesar cada resultado
                for i, listing in enumerate(listings):
                    logger.info(f"Procesando lugar {i+1}/{total_listings}")
                    try:
                        await listing.click()
                        
                        # Esperar a que la página de detalles cargue
                        await page.wait_for_selector('//h1[contains(@class, "DUwDvf")]', timeout=15000)
                        await page.wait_for_timeout(1500)
                        
                        # Selectores para los datos
                        name_xpath = '//h1[contains(@class, "DUwDvf")]'
                        address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                        website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                        phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                        reviews_count_xpath = '//div[contains(@class, "F7nice")]//span[contains(@class, "UY7F9")]'
                        reviews_average_xpath = '//div[contains(@class, "F7nice")]//span[contains(@class, "MW4etd")]'
                        info1 = '//div[contains(@class, "LTs")][@role="img"][1]'
                        info2 = '//div[contains(@class, "LTs")][@role="img"][2]'
                        info3 = '//div[contains(@class, "LTs")][@role="img"][3]'
                        opens_at_xpath = '//div[contains(@class, "OqCZI")]//div[contains(@class, "fontBodyMedium")]'
                        opens_at_xpath2 = '//div[contains(@class, "MkV")]//span[contains(@class, "ZDu")]//span[2]'
                        place_type_xpath = '//button[contains(@class, "DkEaL") and contains(@jsaction, "pane")]'
                        intro_xpath = '//div[contains(@class, "PYvSYb")]'
                        
                        # Extraer datos básicos
                        nombre = await extract_data(name_xpath, page)
                        direccion = await extract_data(address_xpath, page)
                        sitio_web = await extract_data(website_xpath, page)
                        telefono = await extract_data(phone_number_xpath, page)
                        tipo = await extract_data(place_type_xpath, page)
                        
                        # Extraer introducción
                        introduccion = ""
                        if await page.locator(intro_xpath).count() > 0:
                            try:
                                introduccion = await page.locator(intro_xpath).nth(0).inner_text()
                            except Exception:
                                introduccion = ""
                        
                        # Extraer número de reseñas
                        num_reviews = 0
                        if await page.locator(reviews_count_xpath).count() > 0:
                            try:
                                temp = await page.locator(reviews_count_xpath).inner_text()
                                temp = temp.replace('(', '').replace(')', '').replace(',', '')
                                numbers = re.findall(r'\d+', temp)
                                if numbers:
                                    num_reviews = int(numbers[0])
                            except Exception:
                                num_reviews = 0
                        
                        # Extraer promedio de reseñas
                        promedio_reviews = 0.0
                        if await page.locator(reviews_average_xpath).count() > 0:
                            try:
                                temp = await page.locator(reviews_average_xpath).inner_text()
                                temp = temp.replace(' ', '').replace(',', '.')
                                numbers = re.findall(r'\d+\.?\d*', temp)
                                if numbers:
                                    promedio_reviews = float(numbers[0])
                            except Exception:
                                promedio_reviews = 0.0
                        
                        # Información sobre servicios
                        store_shopping = "No"
                        in_store_pickup = "No"
                        store_delivery = "No"
                        
                        # Procesar info1
                        if await page.locator(info1).count() > 0:
                            try:
                                temp = await page.locator(info1).inner_text()
                                temp = temp.split('·')
                                if len(temp) > 1:
                                    check = temp[1].replace("\n", "").lower()
                                    if 'shop' in check:
                                        store_shopping = "Yes"
                                    elif 'pickup' in check:
                                        in_store_pickup = "Yes"
                                    elif 'delivery' in check:
                                        store_delivery = "Yes"
                            except Exception:
                                pass
                        
                        # Procesar info2
                        if await page.locator(info2).count() > 0:
                            try:
                                temp = await page.locator(info2).inner_text()
                                temp = temp.split('·')
                                if len(temp) > 1:
                                    check = temp[1].replace("\n", "").lower()
                                    if 'pickup' in check:
                                        in_store_pickup = "Yes"
                                    elif 'shop' in check:
                                        store_shopping = "Yes"
                                    elif 'delivery' in check:
                                        store_delivery = "Yes"
                            except Exception:
                                pass
                        
                        # Procesar info3
                        if await page.locator(info3).count() > 0:
                            try:
                                temp = await page.locator(info3).inner_text()
                                temp = temp.split('·')
                                if len(temp) > 1:
                                    check = temp[1].replace("\n", "").lower()
                                    if 'delivery' in check:
                                        store_delivery = "Yes"
                                    elif 'pickup' in check:
                                        in_store_pickup = "Yes"
                                    elif 'shop' in check:
                                        store_shopping = "Yes"
                            except Exception:
                                pass
                        
                        # Extraer horario de apertura
                        horario_apertura = ""
                        if await page.locator(opens_at_xpath).count() > 0:
                            try:
                                opens = await page.locator(opens_at_xpath).inner_text()
                                opens = opens.split('⋅')
                                if len(opens) > 1:
                                    opens = opens[1]
                                else:
                                    opens = await page.locator(opens_at_xpath).inner_text()
                                horario_apertura = opens.replace("\u202f", "")
                            except Exception:
                                pass
                        
                        if not horario_apertura and await page.locator(opens_at_xpath2).count() > 0:
                            try:
                                opens = await page.locator(opens_at_xpath2).inner_text()
                                opens = opens.split('⋅')
                                if len(opens) > 1:
                                    opens = opens[1]
                                else:
                                    opens = await page.locator(opens_at_xpath2).inner_text()
                                horario_apertura = opens.replace("\u202f", "")
                            except Exception:
                                pass
                        
                        # Crear objeto restaurante y agregarlo a la lista
                        restaurante = {
                            "nombre": nombre,
                            "direccion": direccion,
                            "sitio_web": sitio_web,
                            "telefono": telefono,
                            "num_reviews": num_reviews,
                            "promedio_reviews": promedio_reviews,
                            "compras_en_tienda": store_shopping,
                            "recogida_en_tienda": in_store_pickup,
                            "entrega": store_delivery,
                            "tipo": tipo,
                            "horario_apertura": horario_apertura,
                            "introduccion": introduccion,
                            "municipio": municipio
                        }
                        
                        restaurantes.append(restaurante)
                    
                    except Exception as e:
                        logger.error(f"Error procesando lugar: {str(e)}")
                        continue
                
                await browser.close()
        except NotImplementedError:
            # Manejar el error específico de Python 3.13 en Windows
            logger.error("Error de compatibilidad detectado (NotImplementedError). Esto puede ocurrir con Python 3.13 en Windows.")
            logger.error("Por favor, intente ejecutar esta aplicación con Python 3.8-3.12 o en un entorno Docker/Linux.")
            raise HTTPException(
                status_code=500, 
                detail="Error de compatibilidad con Playwright. Esto puede ocurrir con Python 3.13 en Windows. " +
                       "Por favor, ejecute la aplicación con Python 3.8-3.12 o en un entorno Docker/Linux."
            )
    
    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al buscar restaurantes: {str(e)}")
    
    tiempo_fin = time.time()
    tiempo_total = tiempo_fin - tiempo_inicio
    
    logger.info(f"Búsqueda completada. Restaurantes encontrados: {len(restaurantes)}")
    logger.info(f"Tiempo de ejecución: {tiempo_total:.2f} segundos")
    
    return {
        "total_resultados": len(restaurantes),
        "restaurantes": restaurantes,
        "tiempo_ejecucion": tiempo_total
    }

# Endpoints de la API
@app.get("/", tags=["Info"])
async def root():
    return {
        "mensaje": "API para buscar restaurantes en municipios de México",
        "documentacion": "/docs",
        "uso": "Envía una solicitud POST a /api/v1/buscar con los parámetros 'municipio' y opcionalmente 'especialidad'"
    }

@app.post("/api/v1/buscar", response_model=SearchResponse, tags=["Búsqueda"])
async def buscar(search_request: SearchRequest):
    """
    Busca restaurantes en un municipio de México con una especialidad específica.
    
    - **municipio**: Nombre del municipio en México (obligatorio)
    - **especialidad**: Tipo de comida o especialidad (opcional)
    - **limite**: Número máximo de resultados a devolver (opcional)
    
    Retorna una lista de restaurantes con sus detalles.
    """
    try:
        resultado = await buscar_restaurantes(
            search_request.municipio,
            search_request.especialidad,
            search_request.limite
        )
        return resultado
    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/buscar", response_model=SearchResponse, tags=["Búsqueda"])
async def buscar_get(
    municipio: str = Query(..., description="Nombre del municipio en México"),
    especialidad: Optional[str] = Query(None, description="Tipo de comida o especialidad"),
    limite: Optional[int] = Query(None, description="Número máximo de resultados a devolver")
):
    """
    Busca restaurantes en un municipio de México con una especialidad específica usando método GET.
    
    - **municipio**: Nombre del municipio en México (obligatorio)
    - **especialidad**: Tipo de comida o especialidad (opcional)
    - **limite**: Número máximo de resultados a devolver (opcional)
    
    Retorna una lista de restaurantes con sus detalles.
    """
    try:
        resultado = await buscar_restaurantes(municipio, especialidad, limite)
        return resultado
    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
