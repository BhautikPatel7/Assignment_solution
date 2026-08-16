"""
estimate.py — Module 5: Cost Estimation Router

POST /api/estimate
  Input:  { session_id, house_height_ft (optional, default 20.0) }
  Flow:
    1. Load session → get segmentation data & material selections
    2. Pass to estimator service
  Output: { estimate_breakdown, totals, metrics }
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from config import logger
from utils import load_session, session_exists, update_session
from services.estimator import generate_estimate

router = APIRouter()

class EstimateRequest(BaseModel):
    session_id: str
    house_height_ft: Optional[float] = 20.0

@router.post("/api/estimate")
async def estimate_cost(req: EstimateRequest):
    """
    Generate a real-world cost estimate based on image pixels and selected materials.
    """
    session_id = req.session_id
    
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session = load_session(session_id)
    seg_data = session.get("segmentation_data")
    material_selections = session.get("material_selections")

    if not seg_data:
        raise HTTPException(
            status_code=400, 
            detail="No segmentation data found. Please complete Module 2."
        )
        
    if not material_selections:
        raise HTTPException(
            status_code=400, 
            detail="No material selections found. Please complete Module 3."
        )

    logger.info(f"[{session_id}] Cost estimation requested (Height: {req.house_height_ft}ft)")

    try:
        estimate_result = generate_estimate(
            seg_data=seg_data,
            material_selections=material_selections,
            house_height_ft=req.house_height_ft
        )
        
        # Save estimate to session for potential PDF generation later
        update_session(session_id, {
            "estimate_data": estimate_result
        })

        return {
            "status": "success",
            "session_id": session_id,
            "data": estimate_result
        }

    except Exception as e:
        logger.error(f"[{session_id}] Estimation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cost estimation failed: {str(e)}")
