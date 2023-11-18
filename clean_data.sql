delete from orders;
delete from trades;
delete from trade_sessions;
delete from algo_udts_scan_records;
delete from algo_slto_track_records;


select * from orders;
select * from trades;
select * from trade_sessions;
select * from algo_udts_scan_records;
select * from algo_slto_track_records;

update dummy_accounts set current_balance=100000 where id=1;



select ins.name as Name,
       udts.market_price as price,
       ord.quantity as quantity,
       ord.order_type as order_type,
       udts.support_price as support_price,
       udts.resistance_price as resistance_price,
       udts.support_strength as support_strength,
       udts.resistance_strength as resistance_strength,
       udts.effective_trend as effective_trend,
       trd.min_price as min_price,
       trd.max_price as max_price,
       trd.margin as margin,
       trd.net_profit as net_profit
       from trades trd join instruments ins on trd.instrument_id=ins.id
       join algo_udts_scan_records udts on trd.id = udts.trade_id
       join orders ord on trd.id = ord.trade_id;




SELECT trades.id AS id, trades.id AS trade_id, trades.started_at AS trade_start_time,trades.closed_at AS trade_end_time, trades.net_profit AS trade_net_profit,instruments.id AS instrument_id, instruments.name AS instrument_name, instruments.trading_symbol AS trading_symbol, trades.view AS trade_view, trades.max_price AS max_price, trades.min_price AS min_price,
SUM(orders.frictional_losses) AS total_frictional_loss,
SUM(orders.quantity) AS traded_quantity,
GROUP_CONCAT(CASE
    WHEN orders.order_type = 'buy' THEN orders.price
    ELSE NULL
END) AS buy_price,
GROUP_CONCAT(CASE
    WHEN orders.order_type = 'sell' THEN orders.price
    ELSE NULL
END) AS sell_price
FROM trades
INNER JOIN instruments ON trades.instrument_id = instruments.id
LEFT JOIN orders ON trades.id = orders.trade_id
WHERE trades.trade_session_id = 70
GROUP BY trades.id;
