from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import uvicorn
import os

app = FastAPI(title="Google Maps Scraper API", 
             description="API para extraer información de restaurantes de Google Maps",
             version="1.0.0")

class SearchGoogleMaps(BaseModel):
    municipality: str
    especiality: str
    limit: int
    
class SearchGoogleMapsResponseItem(BaseModel):
    name: str
    addresse: str
    website: str
    phone_number: str
    # schedule: str
    
class SearchGoogleMapsResponse(BaseModel):
    items: list[SearchGoogleMapsResponseItem]
    
def extract_data(xpath, page):
    """Extract data from a specific xpath or return empty string if not found"""
    if page.locator(xpath).count() > 0:
        return page.locator(xpath).inner_text()
    return ""

@app.get("/")
def read_root():
    return {"message": "Health Check"}

@app.post("/search-google-maps")
def search_google_maps(search_query: SearchGoogleMaps):
    # Validate the limit
    if search_query.limit <= 0:
        return SearchGoogleMapsResponse(items=[])
    
    # Initialize lists to store scraped data
    names_list = []
    address_list = []
    website_list = []
    phones_list = []
    
    with sync_playwright() as p:
        # Setup for Docker environment
        
        # Launch browser with appropriate settings for Docker
        browser_type = p.chromium
        
        browser = browser_type.launch(
            headless=True,
        )
        
        # Configurar el contexto con ubicación de Argentina
        context = browser.new_context(
            locale='es-AR',  # Configurar el idioma como español de Argentina
            timezone_id='America/Argentina/Buenos_Aires',  # Zona horaria de Argentina
            geolocation={'latitude': -34.6037, 'longitude': -58.3816},  # Coordenadas de Buenos Aires
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'es-AR,es;q=0.9',
                # Puedes agregar más encabezados si es necesario
            }
        )
        
        page = context.new_page()

        try:
            # Verificar la geolocalización actual (opcional, para debugging)
            page.goto("https://www.google.com/search?q=mi+ubicacion", timeout=60000)
            page.wait_for_timeout(2000)
            
            # Ahora continuar con Google Maps
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_timeout(1000)

            # Modificar la búsqueda para que sea en Argentina, no en México
            search_term = f"Restaurante {search_query.especiality} en {search_query.municipality}, Argentina"
            page.locator('//input[@id="searchboxinput"]').fill(search_term)
            page.keyboard.press("Enter")
            
            # Wait for search results to appear
            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=30000)
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            # Scroll to load enough listings
            previously_counted = 0
            same_count_iterations = 0
            max_iterations = 20  # Prevent infinite loops
            current_iterations = 0
            
            while current_iterations < max_iterations:
                current_iterations += 1
                
                # Scroll down to load more results
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(1000)  # Give time for results to load
                
                # Get count of current listings
                current_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                print(f"Currently Found: {current_count}")
                
                # Check if we've found enough listings
                if current_count >= search_query.limit:
                    print(f"Found enough listings: {current_count} >= {search_query.limit}")
                    break
                    
                # Check if we've reached all available listings
                if current_count == previously_counted:
                    same_count_iterations += 1
                    if same_count_iterations >= 3:  # If count hasn't changed for 3 iterations, assume we've loaded all available
                        print(f"Reached all available listings: {current_count}")
                        break
                else:
                    same_count_iterations = 0
                    previously_counted = current_count
            
            # Get all available listings
            all_listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
            
            # Limit to the requested number
            listings_to_process = all_listings[:search_query.limit]
            listings_to_process = [listing.locator("xpath=..") for listing in listings_to_process]
            
            print(f"Processing {len(listings_to_process)} listings out of {len(all_listings)} found")
            
            # Define XPaths for the data we need
            name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            
            # Scrape data for each listing
            for listing in listings_to_process:
                try:
                    listing.click()
                    # Wait for listing details to load
                    page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
                    page.wait_for_timeout(1000)
                    
                    # Extract name
                    name = extract_data(name_xpath, page)
                    names_list.append(name)
                    
                    # Extract address
                    address = extract_data(address_xpath, page)
                    address_list.append(address)
                    
                    # Extract website
                    website = extract_data(website_xpath, page)
                    website_list.append(website)
                    
                    # Extract phone number
                    phone = extract_data(phone_xpath, page)
                    phones_list.append(phone)
                    
                except Exception as e:
                    print(f"Error processing listing: {e}")
                    # Add empty values to maintain list alignment
                    names_list.append("")
                    address_list.append("")
                    website_list.append("")
                    phones_list.append("")
        finally:
            # Always close the browser
            browser.close()
        
        # Ensure all lists have the same length by finding the minimum length
        min_length = min(len(names_list), len(address_list), len(website_list), len(phones_list))
        
        # Create response items
        # Create a dictionary to track unique names and their data
        unique_items = {}
        for name, address, website, phone in zip(
            names_list[:min_length],
            address_list[:min_length],
            website_list[:min_length],
            phones_list[:min_length],
        ):
            # Only keep the first occurrence of each name
            if name and name not in unique_items:
                unique_items[name] = {
                    "address": address,
                    "website": website, 
                    "phone": phone
                }
        
        # Convert unique items to response format
        response_items = [
            SearchGoogleMapsResponseItem(
                name=name,
                addresse=data["address"],
                website=data["website"],
                phone_number=data["phone"]
            )
            for name, data in unique_items.items()
        ]

        return SearchGoogleMapsResponse(items=response_items)
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)