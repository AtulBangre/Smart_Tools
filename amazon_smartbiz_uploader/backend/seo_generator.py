import os
import json
from groq import AsyncGroq
import re

# Initialize Groq client later so it doesn't crash if imported before env is loaded
client = None

def get_groq_client():
    global client
    if client is None and os.environ.get("GROQ_API_KEY"):
        client = AsyncGroq()
    return client

async def generate_seo_tags(product_name: str, product_description_html: str) -> dict:
    """
    Generate SEO Meta Title and SEO Meta Description using Groq API.
    """
    groq_client = get_groq_client()
    if not groq_client:
        print("GROQ_API_KEY not found. Skipping SEO generation.")
        return {"seo_title": "", "seo_description": ""}
        
    try:
        # Strip HTML tags from description for the prompt using regex
        plain_desc = re.sub(r'<[^>]+>', ' ', product_description_html)
        plain_desc = re.sub(r'\s+', ' ', plain_desc).strip()
        
        # Limit description length to avoid hitting token limits unnecessarily
        plain_desc = plain_desc[:2000]

        prompt = f"""
Given the following Amazon product name and description, generate an SEO Meta Title (maximum 60 characters) and an SEO Meta Description (maximum 160 characters).
Respond ONLY with a valid JSON object in this exact format, with no markdown formatting or extra text:
{{
    "seo_title": "Your generated title here",
    "seo_description": "Your generated description here"
}}

Product Name: {product_name}
Description: {plain_desc}
"""

        response = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SEO copywriter. You must output only valid JSON without any markdown code blocks like ```json."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        result_content = response.choices[0].message.content
        seo_data = json.loads(result_content)
        
        return {
            "seo_title": seo_data.get("seo_title", "")[:60],
            "seo_description": seo_data.get("seo_description", "")[:160]
        }
    except Exception as e:
        print(f"Error generating SEO tags with Groq: {e}")
        return {"seo_title": "", "seo_description": ""}
