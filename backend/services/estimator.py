"""
estimator.py — Module 5: Cost Estimation Logic

Calculates surface areas, material quantities, and costs based on:
1. Pixel count from segmentation data.
2. Materials selected in Module 3.
3. Predefined base rates (material & labor).
"""

import math

# ── 1. Default Baseline Rates & Coverage ────────────────────────────────
# All prices are in INR (₹)
# Area measurements in Square Feet (sq ft)
# Linear measurements in Running Feet (rft)

MATERIAL_RATES = {
    # Wall Paints (Coverage: ~100 sqft / liter. Costed per sq ft for simplicity)
    'paint': {
        'material_rate_per_sqft': 15.0,  # Premium exterior paint
        'labor_rate_per_sqft': 10.0,
        'wastage_factor': 1.05,          # 5% wastage
        'unit': 'sq ft'
    },
    
    # Textures / Plaster
    'texture_sand.png': { 'material_rate_per_sqft': 35.0, 'labor_rate_per_sqft': 25.0, 'wastage_factor': 1.05, 'unit': 'sq ft' },
    'texture_concrete.png': { 'material_rate_per_sqft': 40.0, 'labor_rate_per_sqft': 30.0, 'wastage_factor': 1.05, 'unit': 'sq ft' },
    'texture_marble.png': { 'material_rate_per_sqft': 150.0, 'labor_rate_per_sqft': 80.0, 'wastage_factor': 1.10, 'unit': 'sq ft' },
    
    # Stone Cladding
    'stone_natural.png': { 'material_rate_per_sqft': 120.0, 'labor_rate_per_sqft': 60.0, 'wastage_factor': 1.10, 'unit': 'sq ft' },
    'stone_slate.png': { 'material_rate_per_sqft': 90.0, 'labor_rate_per_sqft': 50.0, 'wastage_factor': 1.10, 'unit': 'sq ft' },
    'stone_sandstone.png': { 'material_rate_per_sqft': 110.0, 'labor_rate_per_sqft': 55.0, 'wastage_factor': 1.10, 'unit': 'sq ft' },
    'stone_rubble.png': { 'material_rate_per_sqft': 85.0, 'labor_rate_per_sqft': 60.0, 'wastage_factor': 1.15, 'unit': 'sq ft' },
    
    # Roof Tiles
    'roof_clay_tile.png': { 'material_rate_per_sqft': 65.0, 'labor_rate_per_sqft': 35.0, 'wastage_factor': 1.10, 'unit': 'sq ft' },
    'roof_concrete.png': { 'material_rate_per_sqft': 45.0, 'labor_rate_per_sqft': 25.0, 'wastage_factor': 1.05, 'unit': 'sq ft' },
    'roof_metal.png': { 'material_rate_per_sqft': 75.0, 'labor_rate_per_sqft': 30.0, 'wastage_factor': 1.05, 'unit': 'sq ft' },

    # Railings (Costed per running foot - rft)
    'railing_ms_steel.png': { 'material_rate_per_rft': 450.0, 'labor_rate_per_rft': 150.0, 'wastage_factor': 1.0, 'unit': 'rft' },
    'railing_stainless.png': { 'material_rate_per_rft': 850.0, 'labor_rate_per_rft': 200.0, 'wastage_factor': 1.0, 'unit': 'rft' },
    'railing_aluminium.png': { 'material_rate_per_rft': 600.0, 'labor_rate_per_rft': 150.0, 'wastage_factor': 1.0, 'unit': 'rft' },
    'railing_glass.png': { 'material_rate_per_rft': 1200.0, 'labor_rate_per_rft': 300.0, 'wastage_factor': 1.05, 'unit': 'rft' },
    'railing_decorative_iron.png': { 'material_rate_per_rft': 750.0, 'labor_rate_per_rft': 250.0, 'wastage_factor': 1.0, 'unit': 'rft' },
}

# Fallback rates if material not found
DEFAULT_RATE_SQFT = { 'material_rate_per_sqft': 50.0, 'labor_rate_per_sqft': 30.0, 'wastage_factor': 1.10, 'unit': 'sq ft' }
DEFAULT_RATE_RFT  = { 'material_rate_per_rft': 500.0, 'labor_rate_per_rft': 150.0, 'wastage_factor': 1.0, 'unit': 'rft' }


def generate_estimate(seg_data: dict, material_selections: dict, house_height_ft: float = 20.0) -> dict:
    """
    Generate a detailed cost estimate breakdown.
    
    Args:
        seg_data: The output from Module 2 (contains pixel counts, image height).
        material_selections: The user's materials from Module 3 { region_id: { type, value } }.
        house_height_ft: Estimated physical height of the house in feet. Defaults to 20 ft (approx 2 stories).
                         User can override this to scale the entire estimate up/down.
    
    Returns:
        A dictionary containing breakdown by region, grand totals, and conversion metrics.
    """
    image_height_px = seg_data.get("image_height", 1024)
    image_width_px = seg_data.get("image_width", 1024)
    regions = seg_data.get("regions", [])
    
    # ── 1. Calculate Pixel to Real-World Conversion Ratio ──
    # If the image is 1000 pixels high, and the house is 20 feet high:
    # 1 pixel = (20 / 1000) feet
    # 1 square pixel = (20 / 1000)^2 square feet
    ft_per_px = house_height_ft / float(image_height_px)
    sqft_per_sqpx = ft_per_px ** 2

    estimate_breakdown = []
    total_material_cost = 0.0
    total_labor_cost = 0.0

    for region in regions:
        region_id = region["region_id"]
        
        # Only estimate regions that have a material selected
        if region_id not in material_selections:
            continue
            
        selection = material_selections[region_id]
        mat_type = selection.get("type")
        mat_value = selection.get("value")
        
        is_linear = (region_id == "balcony") # Railings are linear (rft)
        
        # ── 2. Calculate Physical Quantity ──
        pixel_count = region.get("pixel_count", 0)
        bbox = region.get("bbox", [0, 0, 0, 0])  # [ymin, xmin, ymax, xmax]
        
        if is_linear:
            # For railings, we estimate length using the bounding box width
            pixel_width = bbox[3] - bbox[1]
            # Actual length in feet = pixel width * ft_per_px
            base_quantity = pixel_width * ft_per_px
        else:
            # For walls, roof, pillars: calculate area in sq ft
            base_quantity = pixel_count * sqft_per_sqpx

        # ── 3. Lookup Rates ──
        rate_info = None
        if mat_type == 'paint':
            rate_info = MATERIAL_RATES['paint']
            mat_name = f"Paint ({mat_value})"
        else:
            rate_info = MATERIAL_RATES.get(mat_value)
            mat_name = mat_value.replace('.png', '').replace('_', ' ').title()

        # Fallbacks
        if not rate_info:
            rate_info = DEFAULT_RATE_RFT if is_linear else DEFAULT_RATE_SQFT

        # ── 4. Apply Wastage and Calculate Costs ──
        wastage_factor = rate_info.get('wastage_factor', 1.0)
        required_quantity = base_quantity * wastage_factor
        
        if is_linear:
            mat_rate = rate_info.get('material_rate_per_rft', 0)
            lab_rate = rate_info.get('labor_rate_per_rft', 0)
        else:
            mat_rate = rate_info.get('material_rate_per_sqft', 0)
            lab_rate = rate_info.get('labor_rate_per_sqft', 0)

        item_mat_cost = required_quantity * mat_rate
        item_lab_cost = required_quantity * lab_rate
        item_total = item_mat_cost + item_lab_cost
        
        total_material_cost += item_mat_cost
        total_labor_cost += item_lab_cost

        estimate_breakdown.append({
            "region_id": region_id,
            "region_name": region_id.replace('_', ' ').title(),
            "material_name": mat_name,
            "unit": rate_info['unit'],
            "base_quantity": round(base_quantity, 2),
            "wastage_factor": wastage_factor,
            "required_quantity": round(required_quantity, 2),
            "material_rate": mat_rate,
            "labor_rate": lab_rate,
            "material_cost": round(item_mat_cost, 2),
            "labor_cost": round(item_lab_cost, 2),
            "total_cost": round(item_total, 2)
        })

    grand_total = total_material_cost + total_labor_cost

    return {
        "metrics": {
            "assumed_house_height_ft": house_height_ft,
            "image_height_px": image_height_px,
            "conversion_sqft_per_sqpx": sqft_per_sqpx
        },
        "breakdown": estimate_breakdown,
        "summary": {
            "total_material_cost": round(total_material_cost, 2),
            "total_labor_cost": round(total_labor_cost, 2),
            "grand_total": round(grand_total, 2)
        }
    }
