#!/usr/bin/env python3
"""
Test runner for RunInitializer tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --integration-only # Run only integration tests
    python run_tests.py --unit-only        # Run only unit tests
    python run_tests.py --verbose          # Run with verbose output
"""

import unittest
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_run_initializer import TestRunInitializer, TestIntegrationScenarios


def run_all_tests(verbosity=1):
    """Run all tests (unit + integration)."""
    print("🚀 Running All Tests (Unit + Integration)")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRunInitializer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n💥 ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if not result.failures and not result.errors:
        print("\n✅ All tests passed!")
    
    return result.wasSuccessful()


def run_integration_tests_only(verbosity=1):
    """Run only integration tests."""
    print("🎯 Running Integration Tests Only")
    print("=" * 50)
    print("Integration tests verify complete trading scenarios and workflows:")
    print("• Complete Trading Scenario - End-to-end trading workflow")
    print("• Bear Market Scenario - Portfolio management during market downturns") 
    print("• Momentum Trading - Multiple entries/exits and profit taking")
    print("• Diversification - Multi-market portfolio management")
    print("• Risk Management - Stop losses and position sizing")
    print("• Long-term Holding - Dollar-cost averaging strategies")
    print("• COMPREHENSIVE STRESS TEST - All functionality + error conditions")
    print("• EXTREME EDGE CASES - Fractional shares + boundary conditions")
    print("=" * 50)
    
    # Create test suite with only integration tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestIntegrationScenarios)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 50)
    print(f"Integration Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
    
    if result.errors:
        print(f"\n💥 ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if not result.failures and not result.errors:
        print("\n✅ All integration tests passed!")
        print("🎉 Your simulation handles complete trading scenarios correctly!")
    
    return result.wasSuccessful()


def run_unit_tests_only(verbosity=1):
    """Run only unit tests."""
    print("🔧 Running Unit Tests Only")
    print("=" * 50)
    print("Unit tests verify individual components and methods:")
    print("• Run creation and management")
    print("• Market creation and updates") 
    print("• Position management (buy/sell)")
    print("• Balance operations")
    print("• Error handling and validation")
    print("=" * 50)
    
    # Create test suite with only unit tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRunInitializer)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 UNIT TEST SUMMARY")
    print("=" * 50)
    print(f"Unit Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n💥 ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if not result.failures and not result.errors:
        print("\n✅ All unit tests passed!")
        print("🎉 All individual components are working correctly!")
    
    return result.wasSuccessful()


def main():
    """Main test runner with command line options."""
    parser = argparse.ArgumentParser(
        description="Run tests for Polymarket Simulation Initialization module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --integration-only # Run only integration tests  
  python run_tests.py --unit-only        # Run only unit tests
  python run_tests.py --verbose          # Run with detailed output
  python run_tests.py --integration-only --verbose  # Verbose integration tests
        """
    )
    
    parser.add_argument(
        '--integration-only', 
        action='store_true',
        help='Run only integration tests (complete trading scenarios)'
    )
    
    parser.add_argument(
        '--unit-only',
        action='store_true', 
        help='Run only unit tests (individual component tests)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Run tests with verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine verbosity level
    verbosity = 2 if args.verbose else 1
    
    # Check for conflicting arguments
    if args.integration_only and args.unit_only:
        print("❌ Error: Cannot specify both --integration-only and --unit-only")
        sys.exit(1)
    
    # Run appropriate test suite
    try:
        if args.integration_only:
            success = run_integration_tests_only(verbosity)
        elif args.unit_only:
            success = run_unit_tests_only(verbosity)
        else:
            success = run_all_tests(verbosity)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 