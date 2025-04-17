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
    schedule: str
    
class SearchGoogleMapsResponse(BaseModel):
    items: list[SearchGoogleMapsResponseItem]
    
def extract_data(xpath, page):
    """Extract data from a specific xpath or return empty string if not found"""
    if page.locator(xpath).count() > 0:
        return page.locator(xpath).inner_text()
    return ""

def extract_schedule(page):
    """Extract complete schedule information from the page"""
    # First try to get the current status (open/closed + next opening time)
    current_status = ""
    current_status_xpath = '//div[@class="MkV9"]//span[@class="ZDu9vd"]//span'
    if page.locator(current_status_xpath).count() > 0:
        current_status = page.locator(current_status_xpath).all_inner_texts()
        current_status = " ".join([text.strip() for text in current_status if text.strip()])
    
    # Try to click the hours dropdown if it exists
    hours_dropdown_xpath = '//div[contains(@class, "OMl5r") and @role="button"]'
    if page.locator(hours_dropdown_xpath).count() > 0:
        try:
            # Click to expand the hours
            page.locator(hours_dropdown_xpath).click()
            page.wait_for_timeout(1000)  # Wait for expansion
        except:
            pass
    
    # Try to get the weekly schedule from the expanded view
    weekly_schedule = ""
    weekly_schedule_xpath = '//table[contains(@class, "eK4R0e")]//tbody//tr'
    
    if page.locator(weekly_schedule_xpath).count() > 0:
        rows = page.locator(weekly_schedule_xpath).all()
        schedule_parts = []
        
        for row in rows:
            try:
                day = row.locator('td[contains(@class, "ylH6lf")]').inner_text().strip()
                hours = row.locator('td[contains(@class, "mxowUb")]').inner_text().strip()
                if day and hours:
                    schedule_parts.append(f"{day}: {hours}")
            except:
                continue
        
        if schedule_parts:
            weekly_schedule = ", ".join(schedule_parts)
    
    # If we got detailed schedule, return it, otherwise return current status
    if weekly_schedule:
        return weekly_schedule
    elif current_status:
        return current_status
    
    # Fallback to the simple schedule xpath as last resort
    simple_schedule_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
    return extract_data(simple_schedule_xpath, page)

@app.get("/")
def read_root():
    return {"message": "Health Check"}

@app.post("/search-google-maps")
def search_google_maps(search_query: SearchGoogleMaps):
    # Validate the limit
    if search_query.limit <= 0:
        return SearchGoogleMapsResponse(items=[])
    
    # Dictionary to store unique restaurants by name to prevent duplicates
    restaurant_dict = {}
    
    with sync_playwright() as p:
        # Setup for Docker environment
        headless = os.environ.get("HEADLESS", "true").lower() == "true"
        
        # Launch browser with appropriate settings for Docker
        browser_type = p.chromium
        
        browser = browser_type.launch(
            headless=headless,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ]
        )
        
        # Set viewport size
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        try:
            # Navigate to Google Maps
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_timeout(1000)

            # Build search query combining municipality and especiality
            search_term = f"Restaurante {search_query.especiality} en Mexico, {search_query.municipality}"
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
                if current_count >= search_query.limit * 2:  # Get more to account for possible duplicates
                    print(f"Found enough listings: {current_count} >= {search_query.limit * 2}")
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
            print(f"Total listings found: {len(all_listings)}")
            
            # Limit to a larger number to account for possible duplicates
            max_to_process = min(len(all_listings), search_query.limit * 2)
            listings_to_process = all_listings[:max_to_process]
            listings_to_process = [listing.locator("xpath=..") for listing in listings_to_process]
            
            print(f"Processing {len(listings_to_process)} listings")
            
            # Define XPaths for the data we need
            name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            
            # Scrape data for each listing
            for i, listing in enumerate(listings_to_process):
                try:
                    # Break the loop if we have enough unique restaurants
                    if len(restaurant_dict) >= search_query.limit:
                        print(f"Reached desired limit of {search_query.limit} unique restaurants")
                        break
                    
                    listing.click()
                    # Wait for listing details to load
                    page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
                    page.wait_for_timeout(2000)
                    
                    # Extract name - this is our unique identifier
                    name = extract_data(name_xpath, page)
                    if not name:  # Skip if no name found
                        print(f"No name found for listing {i+1}, skipping")
                        continue
                    
                    # Extract other data
                    address = extract_data(address_xpath, page)
                    website = extract_data(website_xpath, page)
                    phone = extract_data(phone_xpath, page)
                    schedule = extract_schedule(page)
                    
                    # Only add if we don't already have this restaurant or if we have better data now
                    if name not in restaurant_dict or not restaurant_dict[name].get("schedule"):
                        restaurant_dict[name] = {
                            "name": name,
                            "addresse": address,
                            "website": website,
                            "phone_number": phone,
                            "schedule": schedule
                        }
                        print(f"Added or updated restaurant: {name}")
                    
                except Exception as e:
                    print(f"Error processing listing {i+1}: {e}")
            
        finally:
            # Always close the browser
            browser.close()
        
        # Convert dictionary to list of response items
        response_items = [
            SearchGoogleMapsResponseItem(**item_data)
            for item_data in list(restaurant_dict.values())[:search_query.limit]
        ]
        
        print(f"Returning {len(response_items)} unique restaurants")
        return SearchGoogleMapsResponse(items=response_items)
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)