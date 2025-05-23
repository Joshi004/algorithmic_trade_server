INSERT INTO algorithms (name, display_name, table_name, type, description)
VALUES ('udts', 'Unidirectional Trading Strategy', 'algo_udts_scan_records', 'scanning', '<div><h1>Unidirectional Trading Strategy</h1>
    <p>A unidirectional trading strategy focuses on trading in a single direction, either long (buy) or short (sell), without considering the opposite direction. The main idea behind this strategy is to concentrate on one side of the market and take advantage of trading opportunities in that direction.</p>
    <p>By focusing on a single direction, traders can develop specialized expertise and gain a deeper understanding of the factors driving price movements in that particular direction. This can help them identify potential entry and exit points more effectively.</p>
    <p>Its important to note that unidirectional trading strategies require careful analysis, risk management, and continuous monitoring of market conditions. Its always a good idea to backtest and validate any strategy before applying it with real money.</p></div>');


INSERT INTO algorithms (name, display_name, table_name, type, description)
VALUES ('slto', 'SLTO Strategy', 'algo_slto_track_records', 'tracking', 'System waits for 20th of trade frequency in case of stop loss hit and squares off when price reaches the target');



INSERT INTO user_configurations (user_id, risk_appetite, min_reward_risk_ratio, max_reward_risk_ratio, trades_per_session)
VALUES (1, 5, 2, 15, 100);