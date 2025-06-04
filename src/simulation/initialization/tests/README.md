# Test Suite for Polymarket Simulation Initialization

This directory contains comprehensive tests for the Polymarket Simulation Initialization module.

## Test Structure

- `test_run_initializer.py` - Unit tests and integration tests for the RunInitializer class
- `test_cli.py` - CLI interface tests
- `run_tests.py` - Main test runner with detailed reporting and filtering options

## Test Types

### Unit Tests

Unit tests verify individual components and methods in isolation:

- Test single methods like `create_new_run()`, `add_position()`, `sell_position()`
- Verify specific functionality without complex workflows
- Fast execution and focused on component reliability
- Located in `TestRunInitializer` class

### Integration Tests

Integration tests verify complete end-to-end trading scenarios:

- **Complete Trading Scenario** - Full workflow from run creation to complex trading
- **Bear Market Scenario** - Portfolio management during market downturns and loss cutting
- **Momentum Trading** - Multiple entries/exits, pyramid buying, and profit taking
- **Diversification Scenario** - Multi-market portfolio management and rebalancing
- **Risk Management** - Stop losses, position sizing, and risk control
- **Long-term Holding** - Dollar-cost averaging and long-term investment strategies
- Located in `TestIntegrationScenarios` class

## Running Tests

### Run All Tests (Default)

```bash
# From project root
source venv/bin/activate
python src/simulation/initialization/tests/run_tests.py
```

### Run Only Integration Tests

```bash
# From project root
source venv/bin/activate
python src/simulation/initialization/tests/run_tests.py --integration-only
```

This command will:

- Run only the 6 integration test scenarios
- Provide detailed explanations of what each scenario tests
- Show complete trading workflow results
- Verify end-to-end functionality

### Run Only Unit Tests

```bash
# From project root
source venv/bin/activate
python src/simulation/initialization/tests/run_tests.py --unit-only
```

### Run with Verbose Output

```bash
# Verbose output for all tests
python src/simulation/initialization/tests/run_tests.py --verbose

# Verbose output for integration tests only
python src/simulation/initialization/tests/run_tests.py --integration-only --verbose
```

### Run Individual Test Files

```bash
# Unit tests only
python -m unittest src.simulation.initialization.tests.test_run_initializer.TestRunInitializer -v

# Integration tests only
python -m unittest src.simulation.initialization.tests.test_run_initializer.TestIntegrationScenarios -v
```

### Run Specific Test Cases

```bash
# Run specific integration test
python -m unittest src.simulation.initialization.tests.test_run_initializer.TestIntegrationScenarios.test_bear_market_scenario -v

# Run specific unit test
python -m unittest src.simulation.initialization.tests.test_run_initializer.TestRunInitializer.test_create_new_run_default_name -v
```

## Integration Test Scenarios

### 1. Complete Trading Scenario

Tests the full workflow: run creation → market creation → buying → price updates → selling → balance management. Verifies that all components work together seamlessly.

### 2. Bear Market Scenario

Simulates a market crash where Bitcoin protection fails (-81%) but a contrarian tech recession bet succeeds (+200%). Tests loss cutting and contrarian strategy execution.

### 3. Momentum Trading Scenario

Tests pyramid buying (adding to winners), taking profits at peaks, and managing positions during trending markets. Includes multiple entries and strategic exits.

### 4. Diversification Scenario

Creates a 5-market portfolio across crypto, economics, technology, and politics. Tests equal-weight allocation, rebalancing strategies, and risk distribution.

### 5. Risk Management Scenario

Tests controlled position sizing (5% risk), stop loss execution, and protecting capital during adverse moves. Verifies risk control mechanisms.

### 6. Long-term Holding Scenario

Tests dollar-cost averaging with monthly investments at different price points. Simulates long-term investment strategy with regular additions.

### 7. Comprehensive Trading System Stress Test

**MASSIVE TEST** covering all system functionality including extensive error conditions:

- **10 Markets Across Categories**: Crypto, stocks, economics, politics, technology, climate, sports
- **Position Management**: Success cases, error cases, position merging, negative balance override
- **Market Price Updates**: Multiple volatility scenarios, extreme moves, error handling
- **Position Selling**: Partial sales, complete sales, overselling attempts, error conditions
- **Balance Management**: Add/remove funds, negative amounts, nonexistent runs, override mechanisms
- **Error Testing**: Invalid markets, nonexistent runs, insufficient funds, boundary conditions
- **Final Verification**: Data integrity, transaction counting, portfolio statistics

This test creates 10 markets, makes dozens of positions, simulates market volatility, tests all error conditions, and verifies the system handles complex scenarios robustly.

### 8. Extreme Edge Cases and Fractional Scenarios

**EXTREME TEST** focusing on boundary conditions and fractional precision:

- **Extreme Price Markets**: Near-zero probability (0.000001), near-certain (0.9999), impossible (0.0), certain (1.0)
- **Fractional Positions**: 0.1 shares, 0.001 shares, 0.00001 shares, large quantities of cheap shares
- **Extreme Price Movements**: 95% crashes, 50000% spikes, impossible events becoming possible
- **Fractional Selling**: Selling partial tiny positions with extreme precision (10 decimal places)
- **Balance Precision**: Penny operations (0.01), tenth-cent (0.001), mega operations ($1M+)
- **Mass Operations**: 20 tiny position additions testing merging and system limits
- **Zero/Negative Edge Cases**: Zero shares, negative shares, zero sales (all should fail)
- **Boundary Testing**: Mathematical edge cases, floating-point precision limits

This test pushes the system to its limits with extreme scenarios that would rarely occur in practice but need to be handled correctly.

## Test Coverage

The test suite covers:

### Core Functionality (Unit Tests)

- ✅ **Run Creation** - Default and custom names, JSON structure validation
- ✅ **Market Management** - Creation, duplicate prevention, price tracking
- ✅ **Position Management** - Buy/sell operations, position merging, fractional shares
- ✅ **Balance Management** - Add/remove funds, negative balance handling
- ✅ **Price Updates** - Market price changes, bid/ask spreads, history tracking
- ✅ **Transaction Tracking** - Complete audit trail with profit/loss calculations

### Error Handling (Unit Tests)

- ✅ **Validation** - Missing markets, insufficient funds, invalid inputs
- ✅ **Edge Cases** - Zero balances, duplicate operations, nonexistent data
- ✅ **Financial Protection** - Overdraft prevention with override options

### Complete Workflows (Integration Tests)

- ✅ **End-to-End Trading** - Complete simulation scenarios
- ✅ **Market Scenarios** - Bull/bear markets, momentum, diversification
- ✅ **Trading Strategies** - Risk management, DCA, contrarian betting
- ✅ **Portfolio Management** - Multi-market portfolios and rebalancing
- ✅ **Financial Realism** - Bid/ask spreads, transaction costs, realistic P&L

### Financial Accuracy (Both)

- ✅ **Bid/Ask Pricing** - Realistic trading spreads
- ✅ **Balance Calculations** - Current vs invested vs market value
- ✅ **Profit/Loss Tracking** - Accurate P&L calculations
- ✅ **Transaction History** - Complete financial audit trail

## Expected Results

When all tests pass, you can be confident that:

1. **Component Reliability** (Unit Tests) - Individual methods work correctly
2. **Workflow Integrity** (Integration Tests) - Complete trading scenarios execute properly
3. **Financial Accuracy** - Balance calculations are precise and realistic
4. **Error Prevention** - Invalid operations are properly blocked
5. **Strategy Execution** - Complex trading strategies work as intended

## Test Output Examples

### Integration Test Output

```
🎯 Running Integration Tests Only
Integration tests verify complete trading scenarios and workflows:
• Complete Trading Scenario - End-to-end trading workflow
• Bear Market Scenario - Portfolio management during market downturns
• Momentum Trading - Multiple entries/exits and profit taking
• Diversification - Multi-market portfolio management
• Risk Management - Stop losses and position sizing
• Long-term Holding - Dollar-cost averaging strategies

Integration Tests Run: 6
Success Rate: 100.0%
✅ All integration tests passed!
🎉 Your simulation handles complete trading scenarios correctly!
```

### Unit Test Output

```
🔧 Running Unit Tests Only
Unit tests verify individual components and methods:
• Run creation and management
• Market creation and updates
• Position management (buy/sell)
• Balance operations
• Error handling and validation

Unit Tests Run: 34
Success Rate: 100.0%
✅ All unit tests passed!
🎉 All individual components are working correctly!
```

## Troubleshooting

If tests fail:

1. **Check Virtual Environment** - Ensure `source venv/bin/activate` was run
2. **Verify Working Directory** - Run from project root directory
3. **Check Dependencies** - Ensure all required packages are installed
4. **Review Error Messages** - Test output provides specific failure details
5. **Run Individual Tests** - Isolate failing functionality
6. **Use Integration Tests** - To verify complete workflows work together

## Adding New Tests

When adding new functionality:

1. **Add Unit Tests** - For individual method testing
2. **Add Integration Tests** - For complete workflow testing
3. **Update Test Runner** - If new test categories are needed
4. **Run Full Suite** - Ensure no regressions

The test suite is designed to catch issues early and ensure the simulation system remains reliable and accurate for real-world trading scenarios.
