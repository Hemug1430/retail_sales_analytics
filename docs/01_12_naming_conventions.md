# Tracker 01.12 – Naming Conventions

## 1. Project Folders

* Use lowercase and snake_case.
* Example: `retail_sales_analytics`, `synthetic_data`, `powerbi`, `notebooks`.

## 2. Python Scripts

* Use snake_case.
* Example: `database_connection.py`, `generate_customers.py`, `load_sales_data.py`.

## 3. Jupyter Notebooks

* Prefix with execution order.
* Example: `01_database_connection.ipynb`, `02_customers_generation.ipynb`.

## 4. Database Tables

* Master tables: `<name>_master`
* Transaction tables: `<name>_YYYY_MM`
* Examples: `customers_master`, `products_master`, `sales_2026_09`.

## 5. Database Columns

* Use snake_case.
* IDs end with `_id`.
* Dates end with `_date`.
* Percentages end with `_pct`.
* Examples: `customer_id`, `order_date`, `discount_pct`.

## 6. SQL Views

* Prefix with `vw_`.
* Example: `vw_customer_sales_summary`.

## 7. Power BI Report Pages

* Prefix pages with numbers.
* Example: `01 Executive Dashboard`, `02 Sales Analysis`, `03 Customer Insights`.

## 8. Output Files

* Use snake_case and date format `YYYY_MM_DD`.
* Examples: `customers_master.csv`, `sales_2026_09.csv`, `sales_summary_2026_09_10.csv`.

