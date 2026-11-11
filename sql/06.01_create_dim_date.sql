USE retail_sales_db;

-- ============================================================
-- 06.01 - CREATE DATE DIMENSION DATA
-- Retail Sales Analytics
-- ============================================================

SELECT '06.01 - CREATE DATE DIMENSION DATA' AS step;

-- ------------------------------------------------------------
-- 1. CREATE DATE DIMENSION TABLE
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_date
(
    `date_key` INT NOT NULL,
    `date` DATE NOT NULL,
    `day` TINYINT NOT NULL,
    `day_name` VARCHAR(20) NOT NULL,
    `weekday_number` TINYINT NOT NULL,
    `week` TINYINT NOT NULL,
    `week_start_date` DATE NOT NULL,
    `month_number` TINYINT NOT NULL,
    `month_name` VARCHAR(20) NOT NULL,
    `quarter` VARCHAR(2) NOT NULL,
    `year_quarter` VARCHAR(7) NOT NULL,
    `year` SMALLINT NOT NULL,
    `year_month` CHAR(7) NOT NULL,
    `weekend_flag` VARCHAR(3) NOT NULL,
    `day_type` VARCHAR(10) NOT NULL,

    PRIMARY KEY (`date_key`),
    UNIQUE KEY `uk_dim_date_date` (`date`)
);

-- ------------------------------------------------------------
-- 2. CLEAR EXISTING DATA
-- ------------------------------------------------------------

DELETE FROM dim_date;

-- ------------------------------------------------------------
-- 3. SET RECURSION LIMIT
-- ------------------------------------------------------------

SET SESSION cte_max_recursion_depth = 5000;

-- ------------------------------------------------------------
-- 4. GENERATE COMPLETE CALENDAR
-- ------------------------------------------------------------

INSERT INTO dim_date
(
    `date_key`,
    `date`,
    `day`,
    `day_name`,
    `weekday_number`,
    `week`,
    `week_start_date`,
    `month_number`,
    `month_name`,
    `quarter`,
    `year_quarter`,
    `year`,
    `year_month`,
    `weekend_flag`,
    `day_type`
)

WITH RECURSIVE date_series AS
(
    SELECT DATE('2024-01-01') AS calendar_date

    UNION ALL

    SELECT DATE_ADD(calendar_date, INTERVAL 1 DAY)
    FROM date_series
    WHERE calendar_date < DATE('2027-12-31')
)

SELECT
    CAST(DATE_FORMAT(calendar_date, '%Y%m%d') AS UNSIGNED),

    calendar_date,

    DAY(calendar_date),

    DAYNAME(calendar_date),

    WEEKDAY(calendar_date) + 1,

    WEEK(calendar_date, 3),

    DATE_SUB(
        calendar_date,
        INTERVAL WEEKDAY(calendar_date) DAY
    ),

    MONTH(calendar_date),

    MONTHNAME(calendar_date),

    CONCAT(
        'Q',
        QUARTER(calendar_date)
    ),

    CONCAT(
        YEAR(calendar_date),
        '-Q',
        QUARTER(calendar_date)
    ),

    YEAR(calendar_date),

    DATE_FORMAT(
        calendar_date,
        '%Y-%m'
    ),

    CASE
        WHEN WEEKDAY(calendar_date) >= 5
            THEN 'Yes'
        ELSE 'No'
    END,

    CASE
        WHEN WEEKDAY(calendar_date) >= 5
            THEN 'Weekend'
        ELSE 'Weekday'
    END

FROM date_series
ORDER BY calendar_date;

-- ------------------------------------------------------------
-- 5. VALIDATION 1 - ROW COUNT AND DATE RANGE
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS total_date_rows,
    MIN(`date`) AS minimum_date,
    MAX(`date`) AS maximum_date,
    COUNT(DISTINCT `date`) AS distinct_dates
FROM dim_date;

-- ------------------------------------------------------------
-- 6. VALIDATION 2 - SAMPLE RECORDS
-- ------------------------------------------------------------

SELECT
    `date_key`,
    `date`,
    `day`,
    `day_name`,
    `weekday_number`,
    `week`,
    `week_start_date`,
    `month_number`,
    `month_name`,
    `quarter`,
    `year_quarter`,
    `year`,
    `year_month`,
    `weekend_flag`,
    `day_type`
FROM dim_date
ORDER BY `date`
LIMIT 10;

-- ------------------------------------------------------------
-- 7. VALIDATION 3 - MONTH COVERAGE
-- ------------------------------------------------------------

SELECT
    `year`,
    `month_number`,
    `month_name`,
    COUNT(*) AS days_in_month
FROM dim_date
GROUP BY
    `year`,
    `month_number`,
    `month_name`
ORDER BY
    `year`,
    `month_number`;

-- ------------------------------------------------------------
-- 8. VALIDATION 4 - WEEKEND / WEEKDAY
-- ------------------------------------------------------------

SELECT
    `weekend_flag`,
    `day_type`,
    COUNT(*) AS day_count
FROM dim_date
GROUP BY
    `weekend_flag`,
    `day_type`
ORDER BY
    `weekend_flag`,
    `day_type`;

-- ------------------------------------------------------------
-- 9. FINAL STATUS
-- ------------------------------------------------------------

SELECT
    '06.01 SQL DATE DIMENSION CREATION COMPLETED' AS status;