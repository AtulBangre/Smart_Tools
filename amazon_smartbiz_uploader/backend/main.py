from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import io
from datetime import datetime, timezone
from bson import ObjectId

from database import admin_collection, drafts_collection, sheets_collection, jobs_collection, get_fs
from upload_handler import process_draft_upload
from scraper import scrape_amazon_product
from seo_generator import generate_seo_tags
from excel_handler import generate_smartbiz_excel

app = FastAPI(title="Amazon SmartBiz Uploader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to fix ObjectId serialization
def serialize_doc(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# --- DRAFT ROUTES ---
class DraftItemCreate(BaseModel):
    url: str
    custom_sku: str = ""
    business_category: str = "GENERAL"
    product_category: str = ""
    variant_relationship: str = ""
    size: str = ""
    color_name: str = ""
    best_seller: str = "No"

@app.get("/api/draft")
async def get_drafts():
    cursor = drafts_collection.find({"username": "public_user"})
    items = await cursor.to_list(length=1000)
    return [serialize_doc(i) for i in items]

@app.post("/api/draft/item")
async def add_draft_item(item: DraftItemCreate):
    doc = item.model_dump()
    doc["username"] = "public_user"
    result = await drafts_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@app.delete("/api/draft/item/{item_id}")
async def delete_draft_item(item_id: str):
    result = await drafts_collection.delete_one({"_id": ObjectId(item_id), "username": "public_user"})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success"}

@app.delete("/api/draft/clear")
async def clear_draft():
    await drafts_collection.delete_many({"username": "public_user"})
    return {"status": "success"}

@app.get("/api/draft/template")
async def download_draft_template():
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Draft Template"
    
    headers = [
        "Amazon Link / ASIN", "Custom SKU", "Business Category", 
        "Product Category", "Variant Relationship", "Size", 
        "Color Name", "Best Seller"
    ]
    ws.append(headers)
    
    # Setup Dropdowns (Data Validation)
    # Business Category (Column C)
    categories = '"APPLIANCES,BABY,BEAUTY_AND_PERSONAL_CARE,BOOKS_AND_STATIONERY,CLOTHING,ELECTRONICS,FOOD_AND_GROCERY,FOOTWEAR,FURNITURE,GENERAL,HEALTH_SUPPLEMENTS,HOME_CARE,HOME_AND_KITCHEN,JEWELRY,LAWN_AND_GARDEN,LUGGAGE_AND_BAGS,MULTIPURPOSE,PET_PRODUCTS,SPORTS_AND_FITNESS,TOYS_AND_GAMES,WATCHES"'
    dv_cat = DataValidation(type="list", formula1=categories, allow_blank=True)
    dv_cat.error = 'Your entry is not in the list'
    dv_cat.errorTitle = 'Invalid Entry'
    dv_cat.prompt = 'Please select from the list'
    dv_cat.promptTitle = 'Select Category'
    ws.add_data_validation(dv_cat)
    dv_cat.add("C2:C1000")
    
    # Variant Relationship (Column E)
    dv_var = DataValidation(type="list", formula1='"Parent,Child"', allow_blank=True)
    ws.add_data_validation(dv_var)
    dv_var.add("E2:E1000")
    
    # Best Seller (Column H)
    dv_best = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ws.add_data_validation(dv_best)
    dv_best.add("H2:H1000")
    
    # Adjust column widths slightly for better UX
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        ws.column_dimensions[col].width = 20
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Draft_Upload_Template.xlsx"}
    )

@app.post("/api/draft/upload-excel")
async def upload_excel_draft(file: UploadFile = File(...)):
    return await process_draft_upload(file, drafts_collection, "public_user")

# --- GENERATE & HISTORY ROUTES ---
class GenerateRequest(BaseModel):
    sheet_name: str

async def process_generation_job(job_id: str, items: list, sheet_name: str):
    try:
        scraped_data = []
        total_items = len(items)
        
        for i, item in enumerate(items):
            url = item.get("url", "")
            if not url.startswith("http"):
                url = f"https://www.amazon.in/dp/{url}"
                
            try:
                details = await scrape_amazon_product(url)
                seo_data = await generate_seo_tags(details.get("name", ""), details.get("description", ""))
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                details = {"name": "ERROR", "mrp": "0", "selling_price": "0", "description": "", "images": []}
                seo_data = {"seo_title": "ERROR", "seo_description": "ERROR"}
            
            product_data = {
                "custom_sku": item.get("custom_sku", ""),
                "business_category": item.get("business_category", ""),
                "product_category": item.get("product_category", ""),
                "variant_relationship": item.get("variant_relationship", ""),
                "size": item.get("size", ""),
                "color_name": item.get("color_name", ""),
                "best_seller": item.get("best_seller", ""),
                "name": details.get("name", ""),
                "mrp": details.get("mrp", ""),
                "selling_price": details.get("selling_price", ""),
                "description": details.get("description", ""),
                "images": details.get("images", []),
                "seo_title": seo_data.get("seo_title", ""),
                "seo_description": seo_data.get("seo_description", "")
            }
            scraped_data.append(product_data)
            
            # Update job progress
            await jobs_collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {"processed_count": i + 1, "total_count": total_items}}
            )
            
        # 2. Generate Excel in memory
        template_path = os.path.join(os.path.dirname(__file__), "smartbiz_bulk_upload_template_v5 (2).xlsx")
        temp_output_path = os.path.join(os.path.dirname(__file__), f"temp_{job_id}.xlsx")
        
        success = generate_smartbiz_excel(scraped_data, template_path, temp_output_path)
        if not success:
            raise Exception("Failed to generate Excel file")
            
        # 3. Save to GridFS
        fs = get_fs()
        with open(temp_output_path, "rb") as f:
            file_id = await fs.upload_from_stream(
                f"{sheet_name}.xlsx", 
                f,
                metadata={"contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            )
            
        os.remove(temp_output_path)
        
        # 4. Save history record
        record = {
            "username": "public_user",
            "sheet_name": sheet_name,
            "file_id": file_id,
            "date_generated": datetime.now(timezone.utc).isoformat(),
            "item_count": total_items
        }
        await sheets_collection.insert_one(record)
        
        # 5. Clear draft
        await drafts_collection.delete_many({"username": "public_user"})
        
        # 6. Mark job completed
        await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "completed", "file_id": str(file_id)}}
        )

    except Exception as e:
        print(f"Job failed: {e}")
        await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "failed", "error": str(e)}}
        )

@app.post("/api/generate")
async def generate_excel(request: GenerateRequest, background_tasks: BackgroundTasks):
    # 1. Fetch draft items
    cursor = drafts_collection.find({"username": "public_user"})
    items = await cursor.to_list(length=1000)
    
    if not items:
        raise HTTPException(status_code=400, detail="Your draft is empty.")

    # Create job in db
    job_record = {
        "username": "public_user",
        "sheet_name": request.sheet_name,
        "status": "processing",
        "processed_count": 0,
        "total_count": len(items),
        "date_started": datetime.now(timezone.utc).isoformat()
    }
    result = await jobs_collection.insert_one(job_record)
    job_id = str(result.inserted_id)

    # Trigger background task
    background_tasks.add_task(process_generation_job, job_id, items, request.sheet_name)
    
    return {"status": "processing", "job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = await jobs_collection.find_one({"_id": ObjectId(job_id), "username": "public_user"})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "status": job["status"],
        "processed_count": job.get("processed_count", 0),
        "total_count": job.get("total_count", 0),
        "file_id": job.get("file_id"),
        "error": job.get("error")
    }

@app.get("/api/sheets/history")
async def get_history():
    cursor = sheets_collection.find({"username": "public_user"}).sort("date_generated", -1)
    history = await cursor.to_list(length=100)
    for h in history:
        h["_id"] = str(h["_id"])
        h["file_id"] = str(h["file_id"])
    return history

@app.get("/api/sheets/download/{file_id}")
async def download_sheet(file_id: str):
    fs = get_fs()
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        content = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(content), 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={grid_out.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

@app.delete("/api/sheets/{sheet_id}")
async def delete_sheet(sheet_id: str):
    sheet = await sheets_collection.find_one({"_id": ObjectId(sheet_id), "username": "public_user"})
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet record not found")
        
    fs = get_fs()
    await fs.delete(sheet["file_id"])
    await sheets_collection.delete_one({"_id": ObjectId(sheet_id)})
    return {"status": "success"}

# Mount the frontend static files at the root
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
