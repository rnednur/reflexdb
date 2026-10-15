-- Illustrative StarRocks feature projection. Replace source and field names.
-- Percentiles and HARQ denominators must be verified against actual counters.
SELECT hour_ts, market_id, h3_id, technology,
       dl_throughput_p10 AS throughput,
       sinr_p50 AS sinr,
       dl_harq_failure_rate AS harq,
       dl_prb_utilization AS prb_util,
       sample_count,
       distinct_imsis
FROM network_h3_hourly
WHERE hour_ts >= DATE_SUB(NOW(), INTERVAL 56 DAY);
