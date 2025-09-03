#!/usr/bin/env python3
"""
Form & Function Calc Engine
A Python-based calculation engine for structural steel beam analysis.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import numpy as np
import pandas as pd
from scipy import optimize
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
CALC_ENGINE_PORT = int(os.getenv("PORT", os.getenv("CALC_ENGINE_PORT", "8081")))

app = FastAPI(
    title="Form & Function Calc Engine",
    description="Structural steel beam calculation engine",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class SteelBeam:
    """Steel beam data structure matching the Go API"""
    section_designation: str
    mass_per_metre: float
    depth_of_section: float
    width_of_section: float
    thickness_web: float
    thickness_flange: float
    root_radius: float
    depth_between_fillets: float
    ratios_for_local_buckling_web: float
    ratios_for_local_buckling_flange: float
    end_clearance: float
    notch: float
    dimensions_for_detailing_n: float
    surface_area_per_metre: float
    surface_area_per_tonne: float
    second_moment_of_area_axis_y: float
    second_moment_of_area_axis_z: float
    radius_of_gyration_axis_y: float
    radius_of_gyration_axis_z: float
    elastic_modulus_axis_y: float
    elastic_modulus_axis_z: float
    plastic_modulus_axis_y: float
    plastic_modulus_axis_z: float
    buckling_parameter: float
    torsional_index: float
    warping_constant: float
    torsional_constant: float
    area_of_section: float

class CalculationRequest(BaseModel):
    """Request model for beam calculations"""
    beam_designation: Optional[str] = None
    applied_load: float  # kN
    span_length: float   # m
    load_type: str = "uniform"  # uniform, point, distributed
    safety_factor: float = 1.6
    material_grade: str = "S355"  # Steel grade

class CalculationResult(BaseModel):
    """Response model for calculation results"""
    beam: Dict[str, Any]
    applied_load: float
    span_length: float
    max_moment: float
    max_shear: float
    max_deflection: float
    stress_utilization: float
    deflection_limit_check: bool
    is_adequate: bool
    safety_margin: float
    recommendations: List[str]

class BeamAnalysis:
    """Steel beam analysis calculations using Eurocode 3"""

    def __init__(self):
        self.E = 210000  # N/mm² - Young's modulus for steel
        self.material_strengths = {
            "S235": 235,  # N/mm²
            "S275": 275,
            "S355": 355,
            "S460": 460
        }

    def fetch_beams_from_api(self) -> List[Dict[str, Any]]:
        """Fetch beam data from the Go API"""
        try:
            response = requests.get(f"{API_BASE_URL}/beams", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch beams from API: {e}")
            raise HTTPException(status_code=503, detail="Unable to fetch beam data from API")

    def find_beam(self, designation: str) -> Optional[Dict[str, Any]]:
        """Find a specific beam by designation"""
        beams = self.fetch_beams_from_api()
        for beam in beams:
            if beam["section_designation"] == designation:
                return beam
        return None

    def calculate_moment(self, load: float, span: float, load_type: str = "uniform") -> float:
        """Calculate maximum bending moment based on load type"""
        if load_type == "uniform":
            # Uniformly distributed load: M = wL²/8
            return (load * span**2) / 8
        elif load_type == "point":
            # Point load at center: M = PL/4
            return (load * span) / 4
        else:
            # Default to uniform
            return (load * span**2) / 8

    def calculate_shear(self, load: float, load_type: str = "uniform") -> float:
        """Calculate maximum shear force"""
        if load_type == "uniform":
            # Uniformly distributed load: V = wL/2
            return load / 2
        elif load_type == "point":
            # Point load: V = P/2
            return load / 2
        else:
            return load / 2

    def calculate_deflection(self, load: float, span: float, I: float, load_type: str = "uniform") -> float:
        """Calculate maximum deflection in mm"""
        # Convert I from cm⁴ to mm⁴
        I_mm4 = I * 10000

        if load_type == "uniform":
            # Uniformly distributed load: δ = 5wL⁴/(384EI)
            # Convert load from kN/m to N/mm
            w = load * 1000 / (span * 1000)  # N/mm
            L = span * 1000  # mm
            deflection = (5 * w * L**4) / (384 * self.E * I_mm4)
        elif load_type == "point":
            # Point load at center: δ = PL³/(48EI)
            P = load * 1000  # N
            L = span * 1000  # mm
            deflection = (P * L**3) / (48 * self.E * I_mm4)
        else:
            # Default to uniform
            w = load * 1000 / (span * 1000)
            L = span * 1000
            deflection = (5 * w * L**4) / (384 * self.E * I_mm4)

        return abs(deflection)

    def calculate_stress_utilization(self, moment: float, elastic_modulus: float,
                                   material_grade: str, safety_factor: float = 1.6) -> float:
        """Calculate stress utilization ratio"""
        # Convert moment from kNm to Nmm
        M_Nmm = moment * 1e6
        # Convert elastic modulus from cm³ to mm³
        W_mm3 = elastic_modulus * 1000

        # Calculate actual stress
        actual_stress = M_Nmm / W_mm3  # N/mm²

        # Get material strength
        fy = self.material_strengths.get(material_grade, 355)

        # Calculate allowable stress with safety factor
        allowable_stress = fy / safety_factor

        # Return utilization ratio
        return actual_stress / allowable_stress

    def perform_analysis(self, request: CalculationRequest) -> CalculationResult:
        """Perform comprehensive beam analysis"""

        # Find the beam if designation is provided, otherwise find optimal beam
        if request.beam_designation:
            beam_data = self.find_beam(request.beam_designation)
            if not beam_data:
                raise HTTPException(status_code=404, detail=f"Beam {request.beam_designation} not found")
        else:
            # Find optimal beam based on loading
            beam_data = self.find_optimal_beam(request)

        # Calculate structural responses
        max_moment = self.calculate_moment(request.applied_load, request.span_length, request.load_type)
        max_shear = self.calculate_shear(request.applied_load, request.load_type)
        max_deflection = self.calculate_deflection(
            request.applied_load,
            request.span_length,
            beam_data["second_moment_of_area_axis_y"],
            request.load_type
        )

        # Calculate stress utilization
        stress_utilization = self.calculate_stress_utilization(
            max_moment,
            beam_data["elastic_modulus_axis_y"],
            request.material_grade,
            request.safety_factor
        )

        # Check deflection limits (L/250 for general construction)
        deflection_limit = (request.span_length * 1000) / 250  # mm
        deflection_ok = max_deflection <= deflection_limit

        # Overall adequacy check
        is_adequate = stress_utilization <= 1.0 and deflection_ok

        # Calculate safety margin
        safety_margin = (1.0 - stress_utilization) * 100 if stress_utilization < 1.0 else 0

        # Generate recommendations
        recommendations = self.generate_recommendations(
            stress_utilization, deflection_ok, max_deflection, deflection_limit
        )

        return CalculationResult(
            beam=beam_data,
            applied_load=request.applied_load,
            span_length=request.span_length,
            max_moment=round(max_moment, 2),
            max_shear=round(max_shear, 2),
            max_deflection=round(max_deflection, 2),
            stress_utilization=round(stress_utilization, 3),
            deflection_limit_check=deflection_ok,
            is_adequate=is_adequate,
            safety_margin=round(safety_margin, 1),
            recommendations=recommendations
        )

    def find_optimal_beam(self, request: CalculationRequest) -> Dict[str, Any]:
        """Find the most economical adequate beam"""
        beams = self.fetch_beams_from_api()

        suitable_beams = []

        for beam in beams:
            # Quick check for moment capacity
            max_moment = self.calculate_moment(request.applied_load, request.span_length, request.load_type)
            stress_util = self.calculate_stress_utilization(
                max_moment, beam["elastic_modulus_axis_y"], request.material_grade, request.safety_factor
            )

            # Check deflection
            max_deflection = self.calculate_deflection(
                request.applied_load, request.span_length,
                beam["second_moment_of_area_axis_y"], request.load_type
            )
            deflection_limit = (request.span_length * 1000) / 250

            if stress_util <= 1.0 and max_deflection <= deflection_limit:
                suitable_beams.append({
                    'beam': beam,
                    'mass': beam['mass_per_metre'],
                    'utilization': stress_util
                })

        if not suitable_beams:
            raise HTTPException(status_code=400, detail="No suitable beam found for the given loading")

        # Sort by mass (most economical first)
        suitable_beams.sort(key=lambda x: x['mass'])

        return suitable_beams[0]['beam']

    def generate_recommendations(self, stress_util: float, deflection_ok: bool,
                               actual_deflection: float, deflection_limit: float) -> List[str]:
        """Generate engineering recommendations"""
        recommendations = []

        if stress_util > 1.0:
            recommendations.append(f"CRITICAL: Stress utilization ({stress_util:.2f}) exceeds limit. Consider larger beam section.")
        elif stress_util > 0.9:
            recommendations.append(f"HIGH: Stress utilization ({stress_util:.2f}) is high. Consider reviewing design.")
        elif stress_util < 0.5:
            recommendations.append(f"LOW: Stress utilization ({stress_util:.2f}) is low. Consider smaller section for economy.")

        if not deflection_ok:
            recommendations.append(f"CRITICAL: Deflection ({actual_deflection:.1f}mm) exceeds limit ({deflection_limit:.1f}mm).")
        elif actual_deflection > deflection_limit * 0.8:
            recommendations.append("HIGH: Deflection approaches serviceability limit.")

        if stress_util <= 1.0 and deflection_ok:
            recommendations.append("PASS: Beam is adequate for the applied loading.")

        return recommendations

# Initialize the analysis engine
analyzer = BeamAnalysis()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Form & Function Calc Engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "GET /beams - Get available beams",
            "POST /analyze - Perform beam analysis",
            "GET /health - Health check"
        ]
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test API connectivity
        beams = analyzer.fetch_beams_from_api()
        api_status = "connected"
        beam_count = len(beams)
    except Exception as e:
        api_status = f"disconnected: {str(e)}"
        beam_count = 0

    return {
        "status": "healthy",
        "api_connection": api_status,
        "available_beams": beam_count,
        "calc_engine_port": CALC_ENGINE_PORT
    }

@app.get("/beams")
async def get_beams():
    """Get all available beams from the API"""
    try:
        beams = analyzer.fetch_beams_from_api()
        return {
            "beams": beams,
            "count": len(beams)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch beams: {str(e)}")

@app.post("/analyze", response_model=CalculationResult)
async def analyze_beam(request: CalculationRequest):
    """Perform beam analysis calculations"""
    try:
        result = analyzer.perform_analysis(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/beams/{designation}")
async def get_beam_info(designation: str):
    """Get information about a specific beam"""
    beam = analyzer.find_beam(designation)
    if not beam:
        raise HTTPException(status_code=404, detail=f"Beam {designation} not found")
    return beam

if __name__ == "__main__":
    logger.info(f"Starting Form & Function Calc Engine on port {CALC_ENGINE_PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CALC_ENGINE_PORT,
        reload=False,  # Disable reload for production
        log_level="info"
    )
