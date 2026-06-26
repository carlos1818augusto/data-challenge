USE `looqbox-challenge`;

-- 1) What are the 10 most expensive products in the company?
SELECT
    PRODUCT_COD,
    PRODUCT_NAME,
    PRODUCT_VAL,
    DEP_NAME,
    DEP_COD,
    SECTION_NAME,
    SECTION_COD
FROM data_product
ORDER BY PRODUCT_VAL DESC
LIMIT 10;

-- 2) What sections do the 'BEBIDAS' and 'PADARIA' departments have?
SELECT DISTINCT
    DEP_NAME,
    SECTION_COD,
    SECTION_NAME
FROM data_product
WHERE DEP_NAME IN ('BEBIDAS', 'PADARIA')
ORDER BY DEP_NAME, SECTION_NAME;

-- 3) What was the total sale of products (in $) of each Business Area in the first quarter of 2019?
SELECT
    sc.BUSINESS_NAME,
    ROUND(SUM(ps.SALES_VALUE), 2) AS TOTAL_SALES_VALUE
FROM data_product_sales AS ps
INNER JOIN data_store_cad AS sc
    ON CAST(ps.STORE_CODE AS UNSIGNED) = sc.STORE_CODE
WHERE ps.DATE BETWEEN '2019-01-01' AND '2019-03-31'
GROUP BY sc.BUSINESS_NAME
ORDER BY TOTAL_SALES_VALUE DESC;
