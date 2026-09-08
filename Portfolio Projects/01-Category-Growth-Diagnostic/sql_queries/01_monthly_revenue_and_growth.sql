-- Monthly revenue, orders, AOV, and MoM/YoY growth for the category.
-- Demonstrates: window functions (LAG) for period-over-period growth.

WITH monthly AS (
    SELECT
        year_month,
        COUNT(*)                       AS orders,
        SUM(revenue)                   AS revenue,
        ROUND(SUM(revenue) * 1.0 / COUNT(*), 0) AS aov
    FROM orders
    GROUP BY year_month
)
SELECT
    year_month,
    orders,
    revenue,
    aov,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year_month)) / LAG(revenue) OVER (ORDER BY year_month), 1) AS mom_growth_pct,
    ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (ORDER BY year_month)) / LAG(revenue, 12) OVER (ORDER BY year_month), 1) AS yoy_growth_pct
FROM monthly
ORDER BY year_month;
