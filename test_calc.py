#!/usr/bin/env python3
"""
Test suite for the Form & Function Calculation Engine
Tests gRPC communication with the Go API backend
"""

import sys
import time
import logging
from typing import Dict, Any, List
from grpc_client import SteelBeamGRPCClient, get_beams_grpc, get_beam_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalcEngineTest:
    def __init__(self):
        self.grpc_server_address = "localhost:9090"
        self.calc_engine_url = "http://localhost:8081"  # Keep for internal calc engine HTTP API
        self.test_results = []

    def test_grpc_connectivity(self) -> bool:
        """Test basic gRPC connectivity to Go API"""
        print("Testing gRPC connectivity...")
        try:
            with SteelBeamGRPCClient(self.grpc_server_address) as client:
                beams = client.get_all_beams()
                print(f"✓ gRPC connection successful, retrieved {len(beams)} beams")
                return True
        except Exception as e:
            print(f"✗ gRPC connection failed: {e}")
            return False

    def test_beam_fetch_grpc(self) -> bool:
        """Test fetching beams via gRPC"""
        print("Testing beam fetch via gRPC...")
        try:
            beams = get_beams_grpc(self.grpc_server_address)
            if beams and len(beams) > 0:
                beam_count = len(beams)
                print(f"✓ Successfully fetched {beam_count} beams via gRPC")
                if beam_count > 0:
                    first_beam = beams[0]
                    print(f"  Sample beam: {first_beam['section_designation']}")
                return True
            else:
                print("✗ No beams returned from gRPC API")
                return False
        except Exception as e:
            print(f"✗ Beam fetch via gRPC failed: {e}")
            return False

    def test_specific_beam_grpc(self) -> bool:
        """Test fetching a specific beam via gRPC"""
        print("Testing specific beam lookup via gRPC...")
        try:
            beam_designation = "UB406x178x74"
            beam = get_beam_grpc(beam_designation, self.grpc_server_address)

            if beam:
                print(f"✓ Successfully found beam via gRPC: {beam['section_designation']}")
                print(f"  Mass: {beam['mass_per_metre']} kg/m")
                print(f"  Depth: {beam['depth_of_section']} mm")
                print(f"  Width: {beam['width_of_section']} mm")
                return True
            else:
                print(f"✗ Beam {beam_designation} not found via gRPC")
                return False
        except Exception as e:
            print(f"✗ Specific beam lookup via gRPC failed: {e}")
            return False

    def test_beam_properties(self) -> bool:
        """Test beam property validation"""
        print("Testing beam properties...")
        try:
            beams = get_beams_grpc(self.grpc_server_address)
            if not beams:
                print("✗ No beams to validate")
                return False

            required_fields = [
                'section_designation', 'mass_per_metre', 'depth_of_section',
                'width_of_section', 'thickness_web', 'thickness_flange',
                'second_moment_of_area_axis_y', 'elastic_modulus_axis_y'
            ]

            valid_beams = 0
            for beam in beams:
                if all(field in beam for field in required_fields):
                    valid_beams += 1

            print(f"✓ {valid_beams}/{len(beams)} beams have all required properties")
            return valid_beams == len(beams)

        except Exception as e:
            print(f"✗ Beam property validation failed: {e}")
            return False

    def test_stock_status_grpc(self) -> bool:
        """Test stock status retrieval via gRPC"""
        print("Testing stock status via gRPC...")
        try:
            with SteelBeamGRPCClient(self.grpc_server_address) as client:
                result = client.get_stock_status("test-product-123", "SW1A 1AA")

                if result and 'status' in result:
                    print(f"✓ Stock status retrieved: {result['status']}")
                    print(f"  Product ID: {result['product_id']}")
                    print(f"  Postcode: {result['postcode']}")
                    return True
                else:
                    print("✗ Invalid stock status response")
                    return False
        except Exception as e:
            print(f"✗ Stock status test failed: {e}")
            return False

    def test_beam_analysis_integration(self) -> bool:
        """Test beam analysis with gRPC data"""
        print("Testing beam analysis integration...")

        test_cases = [
            {
                "name": "Simple uniform load",
                "beam_designation": "UB406x178x74",
                "applied_load": 12.0,
                "span_length": 8.0,
                "load_type": "uniform",
                "material_grade": "S355"
            },
            {
                "name": "Point load at center",
                "beam_designation": "UB406x178x67",
                "applied_load": 50.0,
                "span_length": 6.0,
                "load_type": "point",
                "material_grade": "S275"
            }
        ]

        success_count = 0
        for test_case in test_cases:
            try:
                # First verify beam exists via gRPC
                beam = get_beam_grpc(test_case["beam_designation"], self.grpc_server_address)
                if not beam:
                    print(f"✗ {test_case['name']}: Beam not found via gRPC")
                    continue

                # Then test calculation (calc engine still uses HTTP internally)
                import requests
                response = requests.post(
                    f"{self.calc_engine_url}/analyze",
                    json=test_case,
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    self.print_analysis_result(result)
                    print(f"✓ {test_case['name']} analysis completed")
                    success_count += 1
                else:
                    print(f"✗ {test_case['name']}: HTTP {response.status_code}")

            except Exception as e:
                print(f"✗ {test_case['name']} failed: {e}")

        return success_count == len(test_cases)

    def print_analysis_result(self, result: Dict[str, Any]):
        """Print formatted analysis results"""
        if result.get('success'):
            analysis = result.get('analysis', {})
            print(f"    Beam: {analysis.get('beam_designation', 'N/A')}")
            print(f"    Max moment: {analysis.get('max_moment', 'N/A'):.2f} kNm")
            print(f"    Max deflection: {analysis.get('max_deflection', 'N/A'):.2f} mm")
            print(f"    Stress utilization: {analysis.get('stress_utilization', 'N/A'):.1f}%")
            print(f"    Status: {analysis.get('status', 'N/A')}")
        else:
            print(f"    Error: {result.get('error', 'Unknown error')}")

    def run_all_tests(self) -> bool:
        """Run the complete test suite"""
        print("=" * 60)
        print("Form & Function Calc Engine Test Suite (gRPC)")
        print("=" * 60)

        tests = [
            ("gRPC Connectivity", self.test_grpc_connectivity),
            ("Beam Fetch (gRPC)", self.test_beam_fetch_grpc),
            ("Specific Beam (gRPC)", self.test_specific_beam_grpc),
            ("Beam Properties", self.test_beam_properties),
            ("Stock Status (gRPC)", self.test_stock_status_grpc),
            ("Analysis Integration", self.test_beam_analysis_integration),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.test_results.append((test_name, "PASS"))
                else:
                    self.test_results.append((test_name, "FAIL"))
            except Exception as e:
                print(f"✗ {test_name} crashed: {e}")
                self.test_results.append((test_name, "CRASH"))

            time.sleep(0.5)  # Brief pause between tests

        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        for test_name, status in self.test_results:
            status_symbol = "✓" if status == "PASS" else "✗"
            print(f"{status_symbol} {test_name}: {status}")

        print(f"\nOverall: {passed}/{total} tests passed")
        print("=" * 60)

        return passed == total

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        tester = CalcEngineTest()

        # Run specific test
        if hasattr(tester, f"test_{test_name}"):
            test_func = getattr(tester, f"test_{test_name}")
            success = test_func()
            sys.exit(0 if success else 1)
        else:
            print(f"Test '{test_name}' not found")
            sys.exit(1)
    else:
        # Run all tests
        tester = CalcEngineTest()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
