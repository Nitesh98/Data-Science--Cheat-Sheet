-- Average discount vs. order volume by sub-category and month.
-- Feeds the elasticity regression in analysis.py (log-log slope of orders on discount).

SELECT
    sub_category,
    year_month,
    COUNT(*)                              AS orders,
    ROUND(AVG(discount_pct) * 100, 1)     AS avg_discount_pct,
    SUM(revenue)                          AS revenue
FROM orders
GROUP BY sub_category, year_month
ORDER BY sub_category, year_month;
