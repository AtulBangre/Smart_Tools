from playwright.async_api import async_playwright
import re

async def scrape_amazon_product(url: str) -> dict:
    details = {
        "name": "",
        "mrp": "",
        "selling_price": "",
        "description": "",
        "images": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Randomize user agent to help bypass simple checks
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # We wait until domcontentloaded to speed things up since we only need static text mostly
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Scrape Title
            try:
                title_elem = await page.query_selector('#productTitle')
                if title_elem:
                    details["name"] = (await title_elem.inner_text()).strip()[:200]
            except Exception as e:
                print(f"Error scraping title: {e}")

            # Scrape Selling Price
            try:
                # .a-price-whole is commonly used for the main price
                price_elem = await page.query_selector('.priceToPay .a-price-whole, .apexPriceToPay .a-price-whole, #corePrice_feature_div .a-price-whole')
                if price_elem:
                    price_text = await price_elem.inner_text()
                    # Clean up: remove commas, extract numbers
                    raw_price = re.sub(r'[^\d.]', '', price_text)
                    if raw_price:
                        details["selling_price"] = str(int(round(float(raw_price))))
            except Exception as e:
                print(f"Error scraping selling price: {e}")

            # Scrape MRP
            try:
                # .a-text-strike is used for MRP
                mrp_elem = await page.query_selector('.a-text-strike')
                if mrp_elem:
                    mrp_text = await mrp_elem.inner_text()
                    raw_mrp = re.sub(r'[^\d.]', '', mrp_text)
                    if raw_mrp:
                        details["mrp"] = str(int(round(float(raw_mrp))))
                
            # Fallback if MRP isn't there, maybe Selling Price is the MRP
                if not details["mrp"] and details["selling_price"]:
                    details["mrp"] = details["selling_price"]
            except Exception as e:
                print(f"Error scraping MRP: {e}")

            # Default if both are not found
            if not details["mrp"] and not details["selling_price"]:
                details["mrp"] = "1000"
                details["selling_price"] = "800"

            # Scrape Images
            try:
                images = []
                # Find all thumbnail images in the altImages block
                img_elements = await page.query_selector_all('#altImages img')
                
                # If no alt images, try the main image
                if not img_elements:
                    img_elements = await page.query_selector_all('#imgTagWrapperId img, #main-image-container img')
                    
                for img in img_elements:
                    src = await img.get_attribute('src')
                    if src and '.jpg' in src:
                        # Convert thumbnail URL to high res URL as requested by user
                        # Example: https://m.media-amazon.com/images/I/51bIoaFOLLL._AC_US40_.jpg
                        # To: https://m.media-amazon.com/images/I/51bIoaFOLLL._SL1080_.jpg
                        # Regex explanation: match ._ anything _. and replace with ._SL1080_.
                        high_res_url = re.sub(r'\._.*?_\.jpg', '._SL1080_.jpg', src)
                        
                        # Sometimes there is no middle part, just .jpg
                        if high_res_url == src and '._SL1080_' not in high_res_url:
                            high_res_url = src.replace('.jpg', '._SL1080_.jpg')
                            
                        # Avoid duplicates
                        if high_res_url not in images:
                            # Avoid weird non-product icons that are sometimes there like play buttons
                            if "play-button" not in high_res_url and "transparent-pixel" not in high_res_url:
                                images.append(high_res_url)
                        
                        if len(images) >= 6:
                            break
                
                details["images"] = images
            except Exception as e:
                print(f"Error scraping images: {e}")
                details["images"] = []

            # Scrape Description
            try:
                # Extract individual bullet points to construct clean HTML
                bullet_elems = await page.query_selector_all('#feature-bullets ul li span.a-list-item')
                desc_html = ""
                
                if bullet_elems:
                    desc_html = '<ul class="a-unordered-list a-vertical a-spacing-mini">'
                    for elem in bullet_elems:
                        text = (await elem.inner_text()).strip()
                        if text:
                            addition = f'<li class="a-spacing-mini"><span class="a-list-item">{text}</span></li>'
                            # +5 for the closing </ul> tag
                            if len(desc_html) + len(addition) + 5 > 2000:
                                break
                            desc_html += addition
                    desc_html += '</ul>'
                    
                    # If nothing was added (e.g. all were empty), reset
                    if desc_html == '<ul class="a-unordered-list a-vertical a-spacing-mini"></ul>':
                        desc_html = ""
                        
                # Fallback to productDescription if no bullets were found
                if not desc_html:
                    desc_elem = await page.query_selector('#productDescription')
                    if desc_elem:
                        desc_text = (await desc_elem.inner_text()).strip()
                        desc_html = desc_text.replace('\n', '<br>')
                        desc_html = desc_html[:2000]
                
                details["description"] = desc_html
            except Exception as e:
                print(f"Error scraping description: {e}")
                
        except Exception as e:
            print(f"Failed to load {url}: {e}")
        finally:
            await browser.close()
            
    return details
