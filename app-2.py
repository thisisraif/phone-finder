from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import logging
from pathlib import Path
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define input models
class Priority(BaseModel):
    feature: str
    rank: int

class RecommendationRequest(BaseModel):
    budget: str
    priorities: List[Priority]

# Load phone data from Excel file
try:
    logger.info("Loading phone data from Excel file...")
    file_path = Path('C:/Users/admin/OneDrive/Desktop/raifproject/phonedata.xlsx')
    phone_df = pd.read_excel(file_path, engine='openpyxl')
    # Log column names for debugging
    logger.info(f"Excel columns: {phone_df.columns.tolist()}")
    # Log unique Category values to verify available budgets
    unique_categories = phone_df['Category'].dropna().astype(str).str.strip().str.lower().unique().tolist()
    raw_categories = phone_df['Category'].dropna().tolist()
    logger.info(f"Unique Category values (normalized): {unique_categories}")
    logger.info(f"Raw Category values: {raw_categories}")
    # Remove rows with missing Category
    phone_df = phone_df.dropna(subset=["Category"])
    # Convert DataFrame to list of dictionaries
    phone_data = phone_df.to_dict(orient="records")
    # Ensure Total_Score is initialized and log data
    for phone in phone_data:
        phone["Total_Score"] = 0.0
        logger.debug(f"Loaded phone: {phone}")
except Exception as e:
    logger.error(f"Failed to load phone data from Excel: {str(e)}")
    raise Exception(f"Failed to load phone data from Excel: {str(e)}")

@app.get('/')
async def index():
    return {"Message": "Phone Finder API"}

@app.get('/api/categories')
async def get_categories():
    """Return all unique Category values from the Excel file."""
    try:
        unique_categories = sorted(
            phone_df['Category'].dropna().astype(str).str.strip().str.lower().unique().tolist()
        )
        logger.info(f"Returning unique categories: {unique_categories}")
        return {"categories": unique_categories}
    except Exception as e:
        logger.error(f"Failed to fetch categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@app.post('/api/recommend')
async def recommend(request: RecommendationRequest):
    try:
        logger.info(f"Received request: budget={request.budget}, priorities={request.priorities}")
        # Normalize budget for case-insensitive comparison
        budget_normalized = request.budget.strip().lower()
        # Filter phones by Category (case-insensitive), handle missing Category
        filtered_phones = [
            phone for phone in phone_data 
            if "Category" in phone and isinstance(phone["Category"], (str, int, float)) 
            and str(phone["Category"]).strip().lower() == budget_normalized
        ]
        logger.info(f"Filtered {len(filtered_phones)} phones for budget '{request.budget}'")
        # Log details of filtered phones for debugging
        if filtered_phones:
            logger.debug(f"Filtered phones: {[f'{phone.get('Brand', 'Unknown')} {phone.get('Model', 'Unknown')}' for phone in filtered_phones]}")
        else:
            logger.warning(f"No phones found for budget '{request.budget}'. Falling back to mid-range heuristic.")
            # Fallback: Select phones with mid-range characteristics (ratings between 3.5 and 4.5)
            filtered_phones = [
                phone for phone in phone_data
                if all(
                    3.5 <= float(phone.get(key, 0)) <= 4.5
                    for key in ["Brand Rating (5)", "Processor Rating (5)", "Battery Rating (5)", "Camera Rating (5)"]
                )
            ]
            logger.info(f"Fallback found {len(filtered_phones)} mid-range phones")
            if filtered_phones:
                logger.debug(f"Fallback phones: {[f'{phone.get('Brand', 'Unknown')} {phone.get('Model', 'Unknown')}' for phone in filtered_phones]}")
            else:
                logger.warning("No mid-range phones found in fallback. Returning empty results.")

        if not filtered_phones:
            return {"count": 0, "results": []}

        # Calculate scores based on priorities
        for phone in filtered_phones:
            score = 0.0
            for priority in request.priorities:
                weight = (5 - priority.rank)  # Higher rank = higher weight (e.g., rank 1 -> weight 4)
                try:
                    if priority.feature == "brand":
                        score += float(phone["Brand Rating (5)"]) * weight
                    elif priority.feature == "processor":
                        score += float(phone["Processor Rating (5)"]) * weight
                    elif priority.feature == "battery":
                        score += float(phone["Battery Rating (5)"]) * weight
                    elif priority.feature == "camera":
                        score += float(phone["Camera Rating (5)"]) * weight
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error calculating score for phone {phone.get('Brand', 'Unknown')} {phone.get('Model', 'Unknown')}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Invalid data in phone entry: {str(e)}")
            phone["Total_Score"] = score / 16  # Normalize (max weight = 4, 4 features)

        # Sort phones by score and limit to top 3
        sorted_phones = sorted(filtered_phones, key=lambda x: x["Total_Score"], reverse=True)[:3]
        logger.info(f"Returning top {len(sorted_phones)} recommendations")

        # Map the response to match what the frontend expects
        formatted_phones = [
            {
                "Brand": phone["Brand"],
                "Model": phone["Model"],
                "Budget": phone["Category"] if phone in filtered_phones and filtered_phones[0]["Category"] else "Mid-Range (Fallback)",
                "Brand_Rating": float(phone["Brand Rating (5)"]),
                "Processor_Rating": float(phone["Processor Rating (5)"]),
                "Battery_Rating": float(phone["Battery Rating (5)"]),
                "Camera_Rating": float(phone["Camera Rating (5)"]),
                "Total_Score": phone["Total_Score"]
            }
            for phone in sorted_phones
        ]
        
        return {
            "count": len(formatted_phones),
            "results": formatted_phones
        }
    except Exception as e:
        logger.error(f"Recommendation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)