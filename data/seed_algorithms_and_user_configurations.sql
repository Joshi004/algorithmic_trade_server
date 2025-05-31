-- Seed data for algorithm tables

-- Scanning Algorithms
INSERT INTO scanning_algorithms (name, display_name, description)
VALUES 
('UDTS', 'Unidirectional Trading Strategy', '<div>
  <h1>Unidirectional Trading Strategy</h1>
  <p>This strategy focuses on trading in a single direction—either long (buy) or short (sell)—without switching to the opposite side. It aims to capitalize on market trends by maintaining directional bias.</p>
  <p>By specializing in one direction, traders can better analyze market behavior and identify high-probability entry and exit points. This targeted approach enhances decision-making and risk management.</p>
  <p><strong>Key Features:</strong></p>
  <ul>
    <li>Support and resistance level analysis</li>
    <li>Trend strength calculation</li>
    <li>Movement potential assessment</li>
    <li>Real-time market scanning</li>
  </ul>
  <p>Note: Unidirectional strategies require thorough backtesting, ongoing monitoring, and sound risk controls to be effective in live markets.</p>
</div>'),

('RSI_DIVERGENCE', 'RSI Divergence Scanner', '<div>
  <h1>RSI Divergence Scanner</h1>
  <p>Identifies potential reversal opportunities by detecting divergences between price action and RSI (Relative Strength Index) momentum indicator.</p>
  <p><strong>Detection Criteria:</strong></p>
  <ul>
    <li>Bullish divergence: Price makes lower lows while RSI makes higher lows</li>
    <li>Bearish divergence: Price makes higher highs while RSI makes lower highs</li>
    <li>RSI overbought/oversold levels (70/30)</li>
  </ul>
  <p>This scanner is particularly effective in sideways markets and during trend exhaustion phases.</p>
</div>'),

('BREAKOUT_SCANNER', 'Breakout Pattern Scanner', '<div>
  <h1>Breakout Pattern Scanner</h1>
  <p>Identifies stocks breaking out of consolidation patterns with strong volume confirmation.</p>
  <p><strong>Pattern Recognition:</strong></p>
  <ul>
    <li>Rectangle breakouts</li>
    <li>Triangle pattern breakouts</li>
    <li>Flag and pennant patterns</li>
    <li>Volume surge confirmation (2x average volume)</li>
  </ul>
  <p>Filters out false breakouts using multiple timeframe analysis and volume validation.</p>
</div>'),

('MOMENTUM_SURGE', 'Momentum Surge Scanner', '<div>
  <h1>Momentum Surge Scanner</h1>
  <p>Detects sudden momentum shifts in stock prices using multiple technical indicators.</p>
  <p><strong>Indicators Used:</strong></p>
  <ul>
    <li>MACD histogram expansion</li>
    <li>Price rate of change (ROC)</li>
    <li>Average True Range (ATR) expansion</li>
    <li>Volume weighted average price (VWAP) deviation</li>
  </ul>
  <p>Ideal for catching quick momentum moves in intraday trading.</p>
</div>');

-- Initiation Algorithms
INSERT INTO initiation_algorithms (name, display_name, description)
VALUES 
('IMMEDIATE', 'Immediate Initiation', 'The system initiates a trade immediately upon receiving a signal from the scanner. Best for high-confidence signals where timing is critical.'),

('PRICE_CONFIRMATION', 'Price Confirmation Entry', 'Waits for price to confirm the signal direction before entering. For buy signals, waits for price to break above the signal candle high. For sell signals, waits for price to break below the signal candle low.'),

('VOLUME_CONFIRMATION', 'Volume Confirmation Entry', 'Initiates trade only when volume exceeds 1.5x the average volume of the last 20 periods. Ensures institutional participation and reduces false signals.'),

('PULLBACK_ENTRY', 'Pullback Entry Strategy', 'Waits for a minor pullback (3-5%) from the initial signal before entering. This strategy aims to get better entry prices and reduced risk.'),

('ATR_BASED_ENTRY', 'ATR-Based Entry', 'Uses Average True Range (ATR) to determine optimal entry timing. Enters when price moves 0.5x ATR in the signal direction from the scanning point.'),

('FIBONACCI_RETRACEMENT', 'Fibonacci Retracement Entry', 'Waits for price to retrace to key Fibonacci levels (38.2%, 50%, or 61.8%) before initiating the trade. Provides better risk-reward ratios.');

-- Termination Algorithms
INSERT INTO termination_algorithms (name, display_name, description)
VALUES 
('IMMEDIATE', 'Immediate Termination', 'Terminates the trade immediately when exit conditions are met. Provides fastest execution but may miss better exit opportunities.'),

('FIXED_TARGET_STOP', 'Fixed Target/Stop Loss', 'Uses predefined target profit (2:1 or 3:1 risk-reward ratio) and stop loss levels. Simple and systematic approach to trade management.'),

('TRAILING_STOP', 'Trailing Stop Loss', 'Implements a trailing stop that follows the price movement. Allows profits to run while protecting gains. Trail percentage can be customized (1-5%).'),

('ATR_TRAILING', 'ATR-Based Trailing Stop', 'Uses Average True Range (ATR) to set dynamic trailing stops. Adapts to market volatility automatically. Typical setting: 2x ATR trailing distance.'),

('BOLLINGER_EXIT', 'Bollinger Band Exit', 'Exits when price touches the opposite Bollinger Band from entry direction. Effective in mean-reverting markets and range-bound conditions.'),

('TIME_BASED_EXIT', 'Time-Based Exit', 'Closes positions after a predetermined time period regardless of profit/loss. Useful for intraday strategies or when avoiding overnight risk.'),

('VOLUME_DIVERGENCE_EXIT', 'Volume Divergence Exit', 'Monitors volume patterns and exits when volume diverges from price movement, indicating potential trend weakness or reversal.'),

('MULTIPLE_TIMEFRAME_EXIT', 'Multiple Timeframe Exit', 'Uses higher timeframe trend analysis to determine exit timing. Stays in trades when higher timeframe trend is favorable, exits when it turns against the position.');