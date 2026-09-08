-- Where is growth actually coming from -- city tier x sub-category revenue mix,
-- comparing first vs. second year to see which segments are expanding.

SELECT
    CASE WHEN year_month < '2024-01' THEN 'Y1 (2023)' ELSE 'Y2 (2024)' END AS period,
    city_tier,
    sub_category,
    COUNT(*)                       AS orders,
    SUM(revenue)                   AS revenue,
    ROUND(100.0 * SUM(returned) / COUNT(*), 1) AS return_rate_pct
FROM orders
GROUP BY period, city_tier, sub_category
ORDER BY period, city_tier, revenue DESC;
