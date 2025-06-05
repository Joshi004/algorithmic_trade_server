-- Seed data for algorithm tables

-- Scanning Algorithms
INSERT INTO scanning_algorithms (name, display_name, description, is_active)
VALUES 
('UDTS', 'Unidirectional Trading Strategy', 'Focuses on trading in a single direction (long or short) without switching sides. Analyzes support/resistance levels, trend strength, and movement potential to identify high-probability entry points in trending markets.', true),

('RSI_DIVERGENCE', 'RSI Divergence Scanner', 'Detects potential reversal opportunities by identifying divergences between price action and RSI momentum. Looks for bullish divergence (price lower lows, RSI higher lows) and bearish divergence (price higher highs, RSI lower highs).', true),

('BREAKOUT_SCANNER', 'Breakout Pattern Scanner', 'Identifies stocks breaking out of consolidation patterns with strong volume confirmation. Detects rectangle, triangle, flag and pennant breakouts with 2x average volume surge to filter false breakouts.', true),

('MOMENTUM_SURGE', 'Momentum Surge Scanner', 'Detects sudden momentum shifts using MACD histogram expansion, price rate of change, ATR expansion, and VWAP deviation. Ideal for catching quick momentum moves in intraday trading.', true);

-- Initiation Algorithms
INSERT INTO initiation_algorithms (name, display_name, description, is_active)
VALUES 
('IMMEDIATE', 'Immediate Initiation', 'Initiates trade immediately upon receiving scanner signal. Best for high-confidence signals where timing is critical and delays could reduce profit potential.', true),

('PRICE_CONFIRMATION', 'Price Confirmation Entry', 'Waits for price confirmation before entering. For buy signals, waits for price to break above signal candle high. For sell signals, waits for break below signal candle low.', true),

('VOLUME_CONFIRMATION', 'Volume Confirmation Entry', 'Initiates trade only when volume exceeds 1.5x the 20-period average. Ensures institutional participation and reduces false signals from low-volume moves.', true),

('PULLBACK_ENTRY', 'Pullback Entry Strategy', 'Waits for a minor pullback (3-5%) from initial signal before entering. Aims to get better entry prices and reduced risk by entering on temporary weakness.', true),

('ATR_BASED_ENTRY', 'ATR-Based Entry', 'Uses Average True Range to determine optimal entry timing. Enters when price moves 0.5x ATR in signal direction from scanning point, adapting to market volatility.', true),

('FIBONACCI_RETRACEMENT', 'Fibonacci Retracement Entry', 'Waits for price to retrace to key Fibonacci levels (38.2%, 50%, or 61.8%) before initiating trade. Provides better risk-reward ratios by entering on pullbacks.', true);

-- Termination Algorithms
INSERT INTO termination_algorithms (name, display_name, description, is_active)
VALUES 
('IMMEDIATE', 'Immediate Termination', 'Terminates trade immediately when exit conditions are met. Provides fastest execution but may miss better exit opportunities during volatile conditions.', true),

('FIXED_TARGET_STOP', 'Fixed Target/Stop Loss', 'Uses predefined target profit (2:1 or 3:1 risk-reward ratio) and stop loss levels. Simple and systematic approach to trade management with clear exit rules.', true),

('TRAILING_STOP', 'Trailing Stop Loss', 'Implements trailing stop that follows price movement. Allows profits to run while protecting gains. Trail percentage can be customized (typically 1-5%).', true),

('ATR_TRAILING', 'ATR-Based Trailing Stop', 'Uses Average True Range to set dynamic trailing stops that adapt to market volatility automatically. Typical setting is 2x ATR trailing distance for optimal balance.', true),

('BOLLINGER_EXIT', 'Bollinger Band Exit', 'Exits when price touches the opposite Bollinger Band from entry direction. Effective in mean-reverting markets and range-bound conditions with clear boundaries.', true),

('TIME_BASED_EXIT', 'Time-Based Exit', 'Closes positions after predetermined time period regardless of profit/loss. Useful for intraday strategies or when avoiding overnight risk exposure.', true),

('VOLUME_DIVERGENCE_EXIT', 'Volume Divergence Exit', 'Monitors volume patterns and exits when volume diverges from price movement, indicating potential trend weakness or reversal. Helps exit before major moves against position.', true),

('MULTIPLE_TIMEFRAME_EXIT', 'Multiple Timeframe Exit', 'Uses higher timeframe trend analysis to determine exit timing. Stays in trades when higher timeframe trend is favorable, exits when it turns against position.', true);