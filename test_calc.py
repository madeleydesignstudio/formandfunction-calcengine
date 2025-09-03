#!/usr/bin/env python3
"""
Test script for the Form & Function Calc Engine
This script tests the calculation functionality without requiring the web interface.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class CalcEngineTest:
    def __init__(self, calc_engine_url: str = "http://localhost:8081"):
        self.calc_engine_url = calc_engine_url
        self.go_api_url = "http://localhost:8080"

    def test_health_check(self) -> bool:
        """Test if the calc engine is running and healthy"""
        try:
            response = requests.get(f"{self.calc_engine_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✓ Calc Engine Health: {health_data['status']}")
                print(f"  API Connection: {health_data['api_connection']}")
                print(f"  Available Beams: {health_data['available_beams']}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False

    def test_beam_fetch(self) -> bool:
        """Test fetching beam data"""
        try:
            response = requests.get(f"{self.calc_engine_url}/beams", timeout=10)
            if response.status_code == 200:
                beams_data = response.json()
                beam_count = beams_data['count']
                print(f"✓ Successfully fetched {beam_count} beams")
                if beam_count > 0:
                    first_beam = beams_data['beams'][0]
                    print(f"  Sample beam: {first_beam['section_designation']}")
                return True
            else:
                print(f"✗ Beam fetch failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Beam fetch failed: {e}")
            return False

    def test_beam_analysis(self) -> bool:
        """Test beam analysis calculations"""
        test_cases = [
            {
                "name": "Uniform Load Test",
                "request": {
                    "beam_designation": "UB406x178x74",
                    "applied_load": 10.0,  # kN/m
                    "span_length": 6.0,    # m
                    "load_type": "uniform",
                    "safety_factor": 1.6,
                    "material_grade": "S355"
                }
            },
            {
                "name": "Point Load Test",
                "request": {
                    "beam_designation": "UB406x178x67",
                    "applied_load": 50.0,  # kN
                    "span_length": 5.0,    # m
                    "load_type": "point",
                    "safety_factor": 1.6,
                    "material_grade": "S355"
                }
            },
            {
                "name": "Optimal Beam Selection",
                "request": {
                    "applied_load": 15.0,  # kN/m
                    "span_length": 8.0,    # m
                    "load_type": "uniform",
                    "safety_factor": 1.6,
                    "material_grade": "S355"
                }
            }
        ]

        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['name']} ---")
            try:
                response = requests.post(
                    f"{self.calc_engine_url}/analyze",
                    json=test_case['request'],
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    self.print_analysis_result(result)
                    print(f"✓ {test_case['name']} passed")
                else:
                    print(f"✗ {test_case['name']} failed: {response.status_code}")
                    print(f"  Response: {response.text}")
                    all_passed = False

            except Exception as e:
                print(f"✗ {test_case['name']} failed: {e}")
                all_passed = False

        return all_passed

    def print_analysis_result(self, result: Dict[str, Any]):
        """Print analysis results in a readable format"""
        beam = result['beam']
        print(f"  Beam: {beam['section_designation']}")
        print(f"  Applied Load: {result['applied_load']} kN")
        print(f"  Span: {result['span_length']} m")
        print(f"  Max Moment: {result['max_moment']} kNm")
        print(f"  Max Shear: {result['max_shear']} kN")
        print(f"  Max Deflection: {result['max_deflection']:.2f} mm")
        print(f"  Stress Utilization: {result['stress_utilization']:.3f}")
        print(f"  Deflection OK: {result['deflection_limit_check']}")
        print(f"  Overall Adequate: {result['is_adequate']}")
        print(f"  Safety Margin: {result['safety_margin']:.1f}%")

        if result['recommendations']:
            print("  Recommendations:")
            for rec in result['recommendations']:
                print(f"    - {rec}")

    def test_specific_beam_lookup(self) -> bool:
        """Test looking up a specific beam"""
        try:
            beam_designation = "UB406x178x74"
            response = requests.get(
                f"{self.calc_engine_url}/beams/{beam_designation}",
                timeout=5
            )

            if response.status_code == 200:
                beam_data = response.json()
                print(f"✓ Successfully found beam: {beam_data['section_designation']}")
                print(f"  Mass: {beam_data['mass_per_metre']} kg/m")
                print(f"  Depth: {beam_data['depth_of_section']} mm")
                print(f"  Width: {beam_data['width_of_section']} mm")
                return True
            else:
                print(f"✗ Beam lookup failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Beam lookup failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall result"""
        print("=" * 60)
        print("Form & Function Calc Engine Test Suite")
        print("=" * 60)

        tests = [
            ("Health Check", self.test_health_check),
            ("Beam Data Fetch", self.test_beam_fetch),
            ("Specific Beam Lookup", self.test_specific_beam_lookup),
            ("Beam Analysis", self.test_beam_analysis)
        ]

        results = []

        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = test_func()
                results.append(result)
            except Exception as e:
                print(f"✗ {test_name} crashed: {e}")
                results.append(False)

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(results)
        total = len(results)

        for i, (test_name, _) in enumerate(tests):
            status = "✓ PASS" if results[i] else "✗ FAIL"
            print(f"{status} - {test_name}")

        print(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Calc engine is working correctly.")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False

def main():
    """Main test runner"""
    calc_engine_url = "http://localhost:8081"

    # Check if calc engine is specified via command line
    if len(sys.argv) > 1:
        calc_engine_url = sys.argv[1]

    print(f"Testing calc engine at: {calc_engine_url}")
    print("Make sure both the Go API (port 8080) and Calc Engine (port 8081) are running.\n")

    # Wait a moment for services to be ready
    print("Waiting 2 seconds for services to be ready...")
    time.sleep(2)

    tester = CalcEngineTest(calc_engine_url)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
