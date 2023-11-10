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

select* from(
select ins.trading_symbol as Name,
       ord.order_type as order_type,
       ord.quantity as quantity,
       udts.support_price as support_price,
       udts.market_price as price,
       udts.resistance_price as resistance_price,
       udts.effective_trend as effective_trend,
       trd.min_price as min_price,
       trd.max_price as max_price,
       udts.resistance_price - trd.max_price < 0 as sellig_chance,
       trd.min_price - udts.support_price < 0 as buying_chance,
       trd.net_profit as net_profit
       from trades trd join instruments ins on trd.instrument_id=ins.id
       join algo_udts_scan_records udts on trd.id = udts.trade_id
       join orders ord on trd.id = ord.trade_id
       order by ins.name) as t

