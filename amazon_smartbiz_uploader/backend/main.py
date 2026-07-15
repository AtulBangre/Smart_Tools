from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
from scraper import scrape_amazon_product
from seo_generator import generate_seo_tags
from excel_handler import generate_smartbiz_excel
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Amazon SmartBiz Uploader API")

# Add CORS middleware to allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductRequest(BaseModel):
    url: str
    custom_sku: str
    business_category: str
    product_category: str
    variant_relationship: str = ""
    size: str = ""
    color_name: str = ""
    best_seller: str = "No"

class ScrapeRequest(BaseModel):
    products: List[ProductRequest]

@app.post("/api/generate")
async def generate_excel(request: ScrapeRequest):
    try:
        scraped_data = []
        for item in request.products:
            # Check if it's an ASIN or URL
            url = item.url
            if not url.startswith("http"):
                # Construct amazon link if only ASIN is provided
                url = f"https://www.amazon.in/dp/{url}"
            
            # Scrape product details
            details = await scrape_amazon_product(url)
            
            # Generate SEO tags
            seo_data = await generate_seo_tags(details.get("name", ""), details.get("description", ""))
            
            # Combine with user inputs
            product_data = {
                "custom_sku": item.custom_sku,
                "business_category": item.business_category,
                "product_category": item.product_category,
                "variant_relationship": item.variant_relationship,
                "size": item.size,
                "color_name": item.color_name,
                "best_seller": item.best_seller,
                "name": details.get("name", ""),
                "mrp": details.get("mrp", ""),
                "selling_price": details.get("selling_price", ""),
                "description": details.get("description", ""),
                "images": details.get("images", []),
                "seo_title": seo_data.get("seo_title", ""),
                "seo_description": seo_data.get("seo_description", "")
            }
            scraped_data.append(product_data)
        
        # Generate the excel file
        template_path = "/Volumes/Fdata/dev/smartbiz_bulk_upload_template_v5 (2).xlsx"
        output_path = "/Volumes/Fdata/dev/amazon_smartbiz_uploader/backend/Smartbiz_Upload_Generated.xlsx"
        
        success = generate_smartbiz_excel(scraped_data, template_path, output_path)
        
        if success and os.path.exists(output_path):
            return FileResponse(
                path=output_path, 
                filename="Smartbiz_Upload_Generated.xlsx",
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Excel file")
            
    except Exception as e:
        print(f"Error generating excel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
