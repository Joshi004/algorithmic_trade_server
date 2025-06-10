#!/usr/bin/env python3
"""
Script to load seed data for algorithms into the database.
Run this after migrations to populate algorithm tables.

Usage:
    python manage.py shell < data/load_seed_data.py
    
Or from Django shell:
    exec(open('data/load_seed_data.py').read())
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm

def load_scanning_algorithms():
    """Load scanning algorithms seed data"""
    print("Loading scanning algorithms...")
    
    algorithms = [
        {
            'name': 'UDTS',
            'display_name': 'Unidirectional Trading Strategy',
            'description': 'Focuses on trading in a single direction (long or short) without switching sides. Analyzes support/resistance levels, trend strength, and movement potential to identify high-probability entry points in trending markets.',
            'is_active': True
        },
        {
            'name': 'RSI_DIVERGENCE',
            'display_name': 'RSI Divergence Scanner',
            'description': 'Detects potential reversal opportunities by identifying divergences between price action and RSI momentum. Looks for bullish divergence (price lower lows, RSI higher lows) and bearish divergence (price higher highs, RSI lower highs).',
            'is_active': True
        },
        {
            'name': 'BREAKOUT_SCANNER',
            'display_name': 'Breakout Pattern Scanner',
            'description': 'Identifies stocks breaking out of consolidation patterns with strong volume confirmation. Detects rectangle, triangle, flag and pennant breakouts with 2x average volume surge to filter false breakouts.',
            'is_active': True
        },
        {
            'name': 'MOMENTUM_SURGE',
            'display_name': 'Momentum Surge Scanner',
            'description': 'Detects sudden momentum shifts using MACD histogram expansion, price rate of change, ATR expansion, and VWAP deviation. Ideal for catching quick momentum moves in intraday trading.',
            'is_active': True
        }
    ]
    
    for algo_data in algorithms:
        algorithm, created = ScanningAlgorithm.objects.get_or_create(
            name=algo_data['name'],
            defaults=algo_data
        )
        if created:
            print(f"✅ Created scanning algorithm: {algorithm.display_name}")
        else:
            print(f"⚠️  Scanning algorithm already exists: {algorithm.display_name}")

def load_initiation_algorithms():
    """Load initiation algorithms seed data"""
    print("\nLoading initiation algorithms...")
    
    algorithms = [
        {
            'name': 'IMMEDIATE',
            'display_name': 'Immediate Initiation',
            'description': 'Initiates trade immediately upon receiving scanner signal. Best for high-confidence signals where timing is critical and delays could reduce profit potential.',
            'is_active': True
        },
        {
            'name': 'PRICE_CONFIRMATION',
            'display_name': 'Price Confirmation Entry',
            'description': 'Waits for price confirmation before entering. For buy signals, waits for price to break above signal candle high. For sell signals, waits for break below signal candle low.',
            'is_active': True
        },
        {
            'name': 'VOLUME_CONFIRMATION',
            'display_name': 'Volume Confirmation Entry',
            'description': 'Initiates trade only when volume exceeds 1.5x the 20-period average. Ensures institutional participation and reduces false signals from low-volume moves.',
            'is_active': True
        },
        {
            'name': 'PULLBACK_ENTRY',
            'display_name': 'Pullback Entry Strategy',
            'description': 'Waits for a minor pullback (3-5%) from initial signal before entering. Aims to get better entry prices and reduced risk by entering on temporary weakness.',
            'is_active': True
        },
        {
            'name': 'ATR_BASED_ENTRY',
            'display_name': 'ATR-Based Entry',
            'description': 'Uses Average True Range to determine optimal entry timing. Enters when price moves 0.5x ATR in signal direction from scanning point, adapting to market volatility.',
            'is_active': True
        },
        {
            'name': 'FIBONACCI_RETRACEMENT',
            'display_name': 'Fibonacci Retracement Entry',
            'description': 'Waits for price to retrace to key Fibonacci levels (38.2%, 50%, or 61.8%) before initiating trade. Provides better risk-reward ratios by entering on pullbacks.',
            'is_active': True
        }
    ]
    
    for algo_data in algorithms:
        algorithm, created = InitiationAlgorithm.objects.get_or_create(
            name=algo_data['name'],
            defaults=algo_data
        )
        if created:
            print(f"✅ Created initiation algorithm: {algorithm.display_name}")
        else:
            print(f"⚠️  Initiation algorithm already exists: {algorithm.display_name}")

def load_termination_algorithms():
    """Load termination algorithms seed data"""
    print("\nLoading termination algorithms...")
    
    algorithms = [
        {
            'name': 'IMMEDIATE',
            'display_name': 'Immediate Termination',
            'description': 'Terminates trade immediately when exit conditions are met. Provides fastest execution but may miss better exit opportunities during volatile conditions.',
            'is_active': True
        },
        {
            'name': 'FIXED_TARGET_STOP',
            'display_name': 'Fixed Target/Stop Loss',
            'description': 'Uses predefined target profit (2:1 or 3:1 risk-reward ratio) and stop loss levels. Simple and systematic approach to trade management with clear exit rules.',
            'is_active': True
        },
        {
            'name': 'TRAILING_STOP',
            'display_name': 'Trailing Stop Loss',
            'description': 'Implements trailing stop that follows price movement. Allows profits to run while protecting gains. Trail percentage can be customized (typically 1-5%).',
            'is_active': True
        },
        {
            'name': 'ATR_TRAILING',
            'display_name': 'ATR-Based Trailing Stop',
            'description': 'Uses Average True Range to set dynamic trailing stops that adapt to market volatility automatically. Typical setting is 2x ATR trailing distance for optimal balance.',
            'is_active': True
        },
        {
            'name': 'BOLLINGER_EXIT',
            'display_name': 'Bollinger Band Exit',
            'description': 'Exits when price touches the opposite Bollinger Band from entry direction. Effective in mean-reverting markets and range-bound conditions with clear boundaries.',
            'is_active': True
        },
        {
            'name': 'TIME_BASED_EXIT',
            'display_name': 'Time-Based Exit',
            'description': 'Closes positions after predetermined time period regardless of profit/loss. Useful for intraday strategies or when avoiding overnight risk exposure.',
            'is_active': True
        },
        {
            'name': 'VOLUME_DIVERGENCE_EXIT',
            'display_name': 'Volume Divergence Exit',
            'description': 'Monitors volume patterns and exits when volume diverges from price movement, indicating potential trend weakness or reversal. Helps exit before major moves against position.',
            'is_active': True
        },
        {
            'name': 'MULTIPLE_TIMEFRAME_EXIT',
            'display_name': 'Multiple Timeframe Exit',
            'description': 'Uses higher timeframe trend analysis to determine exit timing. Stays in trades when higher timeframe trend is favorable, exits when it turns against position.',
            'is_active': True
        }
    ]
    
    for algo_data in algorithms:
        algorithm, created = TerminationAlgorithm.objects.get_or_create(
            name=algo_data['name'],
            defaults=algo_data
        )
        if created:
            print(f"✅ Created termination algorithm: {algorithm.display_name}")
        else:
            print(f"⚠️  Termination algorithm already exists: {algorithm.display_name}")

def main():
    """Load all seed data"""
    print("🚀 Starting seed data loading...")
    
    try:
        load_scanning_algorithms()
        load_initiation_algorithms()
        load_termination_algorithms()
        
        print("\n✅ Seed data loading completed successfully!")
        print(f"📊 Total algorithms loaded:")
        print(f"   - Scanning: {ScanningAlgorithm.objects.count()}")
        print(f"   - Initiation: {InitiationAlgorithm.objects.count()}")
        print(f"   - Termination: {TerminationAlgorithm.objects.count()}")
        
    except Exception as e:
        print(f"\n❌ Error loading seed data: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 