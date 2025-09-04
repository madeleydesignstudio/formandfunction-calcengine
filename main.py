#!/usr/bin/env python3
"""
Form & Function Calc Engine
A Python-based calculation engine for structural steel beam analysis.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
import numpy as np
import pandas as pd
from scipy import optimize
import uvicorn
from grpc_client import SteelBeamGRPCClient, get_beams_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GRPC_SERVER_ADDRESS = os.getenv("GRPC_SERVER_ADDRESS", "localhost:9090")
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

    def get_embedded_beam_data(self) -> List[Dict[str, Any]]:
        """Fallback beam data when API is unavailable"""
        return [
            {
                "section_designation": "UB406x178x74",
                "mass_per_metre": 74.6,
                "depth_of_section": 412.8,
                "width_of_section": 179.5,
                "thickness_web": 9.3,
                "thickness_flange": 16.0,
                "root_radius": 10.2,
                "depth_between_fillets": 360.8,
                "ratios_for_local_buckling_web": 38.8,
                "ratios_for_local_buckling_flange": 5.61,
                "end_clearance": 369.0,
                "notch": 360.8,
                "dimensions_for_detailing_n": 45.0,
                "surface_area_per_metre": 1.17,
                "surface_area_per_tonne": 15.7,
                "second_moment_of_area_axis_y": 27400,
                "second_moment_of_area_axis_z": 1600,
                "radius_of_gyration_axis_y": 17.1,
                "radius_of_gyration_axis_z": 4.22,
                "elastic_modulus_axis_y": 1330,
                "elastic_modulus_axis_z": 178,
                "plastic_modulus_axis_y": 1500,
                "plastic_modulus_axis_z": 275,
                "buckling_parameter": 0.338,
                "torsional_index": 29.6,
                "warping_constant": 0.581,
                "torsional_constant": 53.8,
                "area_of_section": 95.0
            },
            {
                "section_designation": "UB406x178x67",
                "mass_per_metre": 67.1,
                "depth_of_section": 406.4,
                "width_of_section": 177.9,
                "thickness_web": 8.6,
                "thickness_flange": 12.8,
                "root_radius": 10.2,
                "depth_between_fillets": 360.8,
                "ratios_for_local_buckling_web": 42.0,
                "ratios_for_local_buckling_flange": 6.95,
                "end_clearance": 362.6,
                "notch": 360.8,
                "dimensions_for_detailing_n": 45.0,
                "surface_area_per_metre": 1.15,
                "surface_area_per_tonne": 17.1,
                "second_moment_of_area_axis_y": 23500,
                "second_moment_of_area_axis_z": 1350,
                "radius_of_gyration_axis_y": 16.6,
                "radius_of_gyration_axis_z": 4.09,
                "elastic_modulus_axis_y": 1160,
                "elastic_modulus_axis_z": 152,
                "plastic_modulus_axis_y": 1300,
                "plastic_modulus_axis_z": 234,
                "buckling_parameter": 0.364,
                "torsional_index": 25.4,
                "warping_constant": 0.424,
                "torsional_constant": 36.4,
                "area_of_section": 85.5
            }
        ]

    def fetch_beams_from_api(self) -> List[Dict[str, Any]]:
        """Fetch beam data from the Go API via gRPC with fallback to embedded data"""
        try:
            # Use gRPC to fetch beams
            data = get_beams_grpc(GRPC_SERVER_ADDRESS)

            # Validate the response structure
            if not isinstance(data, list):
                raise ValueError(f"Expected array, got {type(data)}")

            # Validate each beam has required fields
            for beam in data:
                if not isinstance(beam, dict) or 'section_designation' not in beam:
                    raise ValueError("Invalid beam data structure")

            logger.info(f"Successfully fetched {len(data)} beams from Go API via gRPC")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch beams from gRPC API: {e}")
            logger.info("Using embedded data as fallback")
            return self.get_embedded_beam_data()

    def find_beam(self, designation: str) -> Optional[Dict[str, Any]]:
        """Find a specific beam by designation"""
        beams = self.fetch_beams_from_api()
        for beam in beams:
            if beam["section_designation"] == designation:
                return beam
        return None

    def calculate_moment(self, load: float, span: float, load_type: str = "uniform") -> float:
        """Calculate maximum bending moment in kNm"""
        try:
            if load <= 0 or span <= 0:
                raise ValueError("Load and span must be positive values")

            if load_type == "uniform":
                # Uniformly distributed load: M = wL²/8
                moment = (load * span**2) / 8
            elif load_type == "point":
                # Point load at center: M = PL/4
                moment = (load * span) / 4
            else:
                # Default to uniform
                moment = (load * span**2) / 8

            if moment <= 0 or np.isnan(moment) or np.isinf(moment):
                raise ValueError("Invalid moment calculation result")

            return moment
        except Exception as e:
            logger.error(f"Error calculating moment: {str(e)}")
            raise

    def calculate_shear(self, load: float, load_type: str = "uniform") -> float:
        """Calculate maximum shear force"""
        try:
            if load <= 0:
                raise ValueError("Load must be a positive value")

            if load_type == "uniform":
                # Uniformly distributed load: V = wL/2
                shear = load / 2
            elif load_type == "point":
                # Point load: V = P/2
                shear = load / 2
            else:
                shear = load / 2

            if shear <= 0 or np.isnan(shear) or np.isinf(shear):
                raise ValueError("Invalid shear calculation result")

            return shear
        except Exception as e:
            logger.error(f"Error calculating shear: {str(e)}")
            raise

    def calculate_deflection(self, load: float, span: float, I: float, load_type: str = "uniform") -> float:
        """Calculate maximum deflection in mm"""
        try:
            if load <= 0 or span <= 0 or I <= 0:
                raise ValueError("Load, span, and moment of inertia must be positive values")

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

            deflection = abs(deflection)

            if np.isnan(deflection) or np.isinf(deflection):
                raise ValueError("Invalid deflection calculation result")

            return deflection
        except Exception as e:
            logger.error(f"Error calculating deflection: {str(e)}")
            raise

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
        try:
            logger.info(f"Starting beam analysis for: {request.beam_designation or 'optimal beam selection'}")

            # Validate input parameters
            if request.applied_load <= 0:
                raise ValueError("Applied load must be greater than 0")
            if request.span_length <= 0:
                raise ValueError("Span length must be greater than 0")
            if request.safety_factor <= 0:
                raise ValueError("Safety factor must be greater than 0")

            # Find the beam if designation is provided, otherwise find optimal beam
            if request.beam_designation:
                beam_data = self.find_beam(request.beam_designation)
                if not beam_data:
                    raise HTTPException(status_code=404, detail=f"Beam {request.beam_designation} not found")
                logger.info(f"Using specified beam: {request.beam_designation}")
            else:
                # Find optimal beam based on loading
                beam_data = self.find_optimal_beam(request)
                logger.info(f"Selected optimal beam: {beam_data.get('section_designation', 'Unknown')}")

            # Validate beam data has required properties
            required_properties = [
                "second_moment_of_area_axis_y",
                "elastic_modulus_axis_y",
                "section_designation"
            ]
            for prop in required_properties:
                if prop not in beam_data or beam_data[prop] is None:
                    raise ValueError(f"Beam data missing required property: {prop}")

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

            # Validate calculations
            if not all(isinstance(val, (int, float)) and not np.isnan(val) and not np.isinf(val)
                      for val in [max_moment, max_shear, max_deflection, stress_utilization]):
                raise ValueError("Invalid calculation results - NaN or Inf values detected")

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

            logger.info(f"Analysis completed successfully for beam: {beam_data['section_designation']}")

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

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except ValueError as e:
            logger.error(f"Validation error in beam analysis: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
        except KeyError as e:
            logger.error(f"Missing data in beam analysis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Missing beam property: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in beam analysis: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Analysis calculation failed: {str(e)}")

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
    """Health check endpoint that tests connectivity to the Go API via gRPC"""
    try:
        # Test gRPC API connectivity
        beams = get_beams_grpc(GRPC_SERVER_ADDRESS)
        api_status = "connected"
        beam_count = len(beams)
        data_source = "go_api_grpc"
    except Exception as e:
        # Fallback to embedded data
        embedded_beams = analyzer.get_embedded_beam_data()
        api_status = f"using_fallback: {str(e)}"
        beam_count = len(embedded_beams)
        data_source = "embedded"

    return {
        "status": "healthy",
        "api_connection": api_status,
        "available_beams": beam_count,
        "data_source": data_source,
        "grpc_address": GRPC_SERVER_ADDRESS
    }

@app.get("/beams")
async def get_beams():
    """Get all available beams from the API or embedded data"""
    try:
        beams = analyzer.fetch_beams_from_api()
        return {
            "beams": beams,
            "count": len(beams),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in get_beams endpoint: {str(e)}")
        # Fallback to embedded data
        try:
            embedded_beams = analyzer.get_embedded_beam_data()
            return {
                "beams": embedded_beams,
                "count": len(embedded_beams),
                "status": "fallback",
                "error": str(e)
            }
        except Exception as fallback_error:
            logger.error(f"Failed to get embedded beams: {str(fallback_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch beams: {str(e)}")


@app.post("/analyze", response_model=CalculationResult)
async def analyze_beam(raw_request: FastAPIRequest):
    """Perform beam analysis calculations"""
    try:
        # Log raw request for debugging
        body = await raw_request.body()
        logger.info(f"Raw request body: {body.decode()}")
        logger.info(f"Content-Type: {raw_request.headers.get('content-type')}")

        # Parse JSON manually for better error handling
        try:
            json_data = json.loads(body.decode())
            logger.info(f"Parsed JSON: {json_data}")
            logger.info(f"JSON type: {type(json_data)}")
        except json.JSONDecodeError as json_e:
            logger.error(f"JSON parsing error: {json_e}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(json_e)}")

        # Show what we expect vs what we got
        logger.info(f"Expected CalculationRequest fields: {list(CalculationRequest.__fields__.keys())}")
        logger.info(f"Received JSON keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")

        # Validate against Pydantic model
        try:
            request = CalculationRequest(**json_data)
            logger.info(f"Successfully created CalculationRequest: {request}")
        except ValidationError as model_e:
            logger.error(f"Pydantic validation error: {model_e}")
            error_details = []
            for error in model_e.errors():
                error_details.append({
                    "field": error.get("loc", []),
                    "message": error.get("msg", ""),
                    "type": error.get("type", ""),
                    "input": error.get("input", "")
                })
            raise HTTPException(status_code=400, detail=error_details)
        except Exception as model_e:
            logger.error(f"General model validation error: {model_e}")
            raise HTTPException(status_code=400, detail=f"Validation error: {str(model_e)}")

        logger.info(f"Starting analysis for request: {request}")
        result = analyzer.perform_analysis(request)
        logger.info("Analysis completed successfully")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analyze/test-format")
async def get_analyze_format():
    """Get the expected format for the analyze endpoint"""
    return {
        "endpoint": "POST /analyze",
        "expected_format": {
            "beam_designation": "UB406x178x74 (optional - if not provided, will find optimal beam)",
            "applied_load": 15.0,
            "span_length": 8.0,
            "load_type": "uniform",
            "safety_factor": 1.6,
            "material_grade": "S355"
        },
        "example_request": {
            "applied_load": 12.5,
            "span_length": 6.0,
            "load_type": "uniform",
            "safety_factor": 1.6,
            "material_grade": "S355"
        },
        "notes": {
            "applied_load": "Applied load in kN",
            "span_length": "Span length in meters",
            "load_type": "Either 'uniform', 'point', or 'distributed'",
            "safety_factor": "Safety factor (default 1.6)",
            "material_grade": "Steel grade (S235, S275, S355, S460)",
            "beam_designation": "Optional - leave empty for optimal beam selection"
        }
    }

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
