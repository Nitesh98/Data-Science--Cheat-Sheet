-- Classic cohort retention table: of customers ACQUIRED in a given month,
-- what % placed an order again N months later?
-- Demonstrates: self-join-free cohort analysis using conditional aggregation.

WITH cohort_size AS (
    SELECT year_month AS cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM orders
    WHERE is_new_customer = 1
    GROUP BY year_month
),
cohort_activity AS (
    SELECT
        o_acq.year_month           AS cohort_month,
        o_any.months_since_acquisition AS month_number,
        COUNT(DISTINCT o_any.customer_id) AS active_customers
    FROM orders o_acq
    JOIN orders o_any ON o_any.customer_id = o_acq.customer_id
    WHERE o_acq.is_new_customer = 1
    GROUP BY o_acq.year_month, o_any.months_since_acquisition
)
SELECT
    a.cohort_month,
    s.cohort_customers,
    a.month_number,
    a.active_customers,
    ROUND(100.0 * a.active_customers / s.cohort_customers, 1) AS retention_pct
FROM cohort_activity a
JOIN cohort_size s ON s.cohort_month = a.cohort_month
WHERE a.month_number <= 6
ORDER BY a.cohort_month, a.month_number;
