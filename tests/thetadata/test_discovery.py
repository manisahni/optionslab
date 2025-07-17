#!/usr/bin/env python3
"""Test script to verify the discovery functions work correctly."""

import asyncio
from datetime import datetime
from thetadata.discovery import discover_options_contracts, discover_bulk_option_contracts_v1
from thetadata.client import ThetaDataTerminalClient

async def test_discover_options_contracts():
    """Test the discover_options_contracts function."""
    print("=" * 60)
    print("Testing discover_options_contracts")
    print("=" * 60)
    
    # Test parameters
    symbol = "SPY"
    target_dte = 30  # Looking for options expiring in about 30 days
    strike_range = (400, 500)  # Strike price range
    right = "C"  # Calls
    
    print(f"\nParameters:")
    print(f"Symbol: {symbol}")
    print(f"Target DTE: {target_dte} days")
    print(f"Strike Range: ${strike_range[0]} - ${strike_range[1]}")
    print(f"Right: {right} (Call)")
    
    try:
        # Run discovery
        contracts = await discover_options_contracts(
            symbol=symbol,
            target_dte=target_dte,
            strike_range=strike_range,
            right=right,
            dte_window=5,  # Allow +/- 5 days from target
            verbose=True
        )
        
        print(f"\nFound {len(contracts)} contracts")
        if contracts:
            print("\nFirst 5 contracts:")
            for i, contract in enumerate(contracts[:5]):
                print(f"  {i+1}. {contract['root']} {contract['exp']} ${contract['strike']} {contract['right']}")
    
    except Exception as e:
        print(f"Error in discover_options_contracts: {e}")
        return False
    
    return True

async def test_discover_bulk_option_contracts_v1():
    """Test the discover_bulk_option_contracts_v1 function."""
    print("\n" + "=" * 60)
    print("Testing discover_bulk_option_contracts_v1")
    print("=" * 60)
    
    # Test parameters
    symbol = "AAPL"
    target_dte = 14  # Looking for options expiring in about 2 weeks
    strike_range = (170, 200)  # Strike price range
    right = "P"  # Puts
    
    print(f"\nParameters:")
    print(f"Symbol: {symbol}")
    print(f"Target DTE: {target_dte} days")
    print(f"Strike Range: ${strike_range[0]} - ${strike_range[1]}")
    print(f"Right: {right} (Put)")
    
    try:
        async with ThetaDataTerminalClient() as client:
            # Run discovery
            contracts = await discover_bulk_option_contracts_v1(
                client=client,
                symbol=symbol,
                target_dte=target_dte,
                strike_range=strike_range,
                right=right,
                dte_window=3,  # Allow +/- 3 days from target
                verbose=True
            )
            
            print(f"\nFound {len(contracts)} contracts")
            if contracts:
                print("\nFirst 5 contracts:")
                for i, contract in enumerate(contracts[:5]):
                    print(f"  {i+1}. {contract['root']} {contract['exp']} ${contract['strike']} {contract['right']}")
    
    except Exception as e:
        print(f"Error in discover_bulk_option_contracts_v1: {e}")
        return False
    
    return True

async def test_bulk_quotes():
    """Test getting bulk quotes for discovered contracts."""
    print("\n" + "=" * 60)
    print("Testing bulk quotes retrieval")
    print("=" * 60)
    
    symbol = "SPY"
    
    try:
        async with ThetaDataTerminalClient() as client:
            # Get expirations
            expirations = await client.list_option_expirations(symbol)
            print(f"\nAvailable expirations for {symbol}: {len(expirations)}")
            print(f"First 5 expirations: {expirations[:5]}")
            
            # Use the first expiration
            if expirations:
                exp = expirations[0]
                print(f"\nGetting bulk quotes for expiration: {exp}")
                
                # Get bulk quotes
                bulk_quotes = await client.get_bulk_option_quotes(symbol, exp)
                print(f"Received {len(bulk_quotes)} quotes")
                
                # Show sample data
                if bulk_quotes and len(bulk_quotes) > 0:
                    print("\nSample quote data:")
                    for i, quote in enumerate(bulk_quotes[:3]):
                        if isinstance(quote, dict):
                            print(f"  Contract {i+1}: Strike=${quote.get('strike', 'N/A')}, "
                                  f"Right={quote.get('right', 'N/A')}, "
                                  f"Bid=${quote.get('bid', 'N/A')}, "
                                  f"Ask=${quote.get('ask', 'N/A')}")
    
    except Exception as e:
        print(f"Error in bulk quotes test: {e}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("Starting discovery function tests...\n")
    
    # Run tests
    test1 = await test_discover_options_contracts()
    test2 = await test_discover_bulk_option_contracts_v1()
    test3 = await test_bulk_quotes()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"discover_options_contracts: {'PASSED' if test1 else 'FAILED'}")
    print(f"discover_bulk_option_contracts_v1: {'PASSED' if test2 else 'FAILED'}")
    print(f"bulk_quotes: {'PASSED' if test3 else 'FAILED'}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())