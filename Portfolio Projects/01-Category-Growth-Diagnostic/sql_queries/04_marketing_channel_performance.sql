-- Channel mix and quality: orders, revenue, share of NEW customer acquisition,
-- and return rate by marketing channel. Useful for a "where should growth
-- budget shift" recommendation.

SELECT
    marketing_channel,
    COUNT(*)                                            AS orders,
    SUM(revenue)                                        AS revenue,
    SUM(is_new_customer)                                AS new_customer_orders,
    ROUND(100.0 * SUM(is_new_customer) / COUNT(*), 1)   AS pct_of_orders_are_new,
    ROUND(100.0 * SUM(returned) / COUNT(*), 1)          AS return_rate_pct,
    ROUND(SUM(revenue) * 1.0 / COUNT(*), 0)             AS aov
FROM orders
GROUP BY marketing_channel
ORDER BY revenue DESC;
