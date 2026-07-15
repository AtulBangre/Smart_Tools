import pandas as pd
from io import BytesIO
from fastapi import UploadFile, HTTPException

async def process_draft_upload(file: UploadFile, db_collection, username: str):
    """
    Reads an uploaded Excel file, extracts rows, and saves them to the draft.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported for upload.")
        
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Expected columns (case insensitive, approximate matches)
        # We need to map them to: url, custom_sku, business_category, product_category, variant_relationship, size, color_name, best_seller
        
        # To make it robust, let's normalize column names
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        
        items_to_insert = []
        for index, row in df.iterrows():
            # Basic validation: needs at least a URL or ASIN
            url = row.get('amazon_link_/_asin') or row.get('url') or row.get('link') or row.get('asin')
            if pd.isna(url) or str(url).strip() == '':
                continue
                
            item = {
                "username": username, # link to the admin
                "url": str(url).strip(),
                "custom_sku": str(row.get('custom_sku', '')).strip() if not pd.isna(row.get('custom_sku')) else "",
                "business_category": str(row.get('business_category', '')).strip() if not pd.isna(row.get('business_category')) else "GENERAL",
                "product_category": str(row.get('product_category', '')).strip() if not pd.isna(row.get('product_category')) else "",
                "variant_relationship": str(row.get('variant_relationship', '')).strip() if not pd.isna(row.get('variant_relationship')) else "",
                "size": str(row.get('size', '')).strip() if not pd.isna(row.get('size')) else "",
                "color_name": str(row.get('color_name', '')).strip() if not pd.isna(row.get('color_name')) else "",
                "best_seller": "Yes" if str(row.get('best_seller', '')).strip().lower() in ['yes', 'y', '1', 'true'] else "No"
            }
            items_to_insert.append(item)
            
        if items_to_insert:
            # Clear existing draft for user
            await db_collection.delete_many({"username": username})
            # Insert new ones
            await db_collection.insert_many(items_to_insert)
            return {"message": f"Successfully loaded {len(items_to_insert)} items into your draft."}
        else:
            raise HTTPException(status_code=400, detail="No valid rows found in the uploaded file.")
            
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
