-- ============================================================
-- ITCS-6190 Assignment 3 — Athena SQL Queries
-- Database : orders_db
-- Table    : filtered_orders  (created by Glue Crawler)
-- ============================================================

-- Query 1: Total Sales by Customer
-- Cumulative revenue per customer, highest first
SELECT
    Customer,
    ROUND(SUM(Amount), 2) AS TotalAmountSpent
FROM "filtered_orders"
GROUP BY Customer
ORDER BY TotalAmountSpent DESC;

-- ============================================================

-- Query 2: Monthly Order Volume and Revenue
-- Order count and revenue aggregated by calendar month
SELECT
    DATE_TRUNC('month', CAST(OrderDate AS DATE)) AS OrderMonth,
    COUNT(OrderID)              AS NumberOfOrders,
    ROUND(SUM(Amount), 2)       AS MonthlyRevenue
FROM "filtered_orders"
GROUP BY 1
ORDER BY OrderMonth;

-- ============================================================

-- Query 3: Order Status Dashboard
-- Count and revenue broken down by fulfilment status
SELECT
    Status,
    COUNT(OrderID)        AS OrderCount,
    ROUND(SUM(Amount), 2) AS TotalAmount
FROM "filtered_orders"
GROUP BY Status
ORDER BY OrderCount DESC;

-- ============================================================

-- Query 4: Average Order Value (AOV) per Customer
-- Mean spend per order for each customer
SELECT
    Customer,
    ROUND(AVG(Amount), 2) AS AverageOrderValue
FROM "filtered_orders"
GROUP BY Customer
ORDER BY AverageOrderValue DESC;

-- ============================================================

-- Query 5: Top 10 Largest Orders in February 2025
-- Highest-value individual orders placed during Feb 2025
SELECT
    OrderDate,
    OrderID,
    Customer,
    ROUND(Amount, 2) AS Amount
FROM "filtered_orders"
WHERE CAST(OrderDate AS DATE)
      BETWEEN DATE '2025-02-01' AND DATE '2025-02-28'
ORDER BY Amount DESC
LIMIT 10;
