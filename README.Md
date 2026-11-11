Retail Sales Analytics - End-to-End Data Analytics Project

## Project Purpose

This project is an end-to-end Retail Sales Analytics solution that analyzes retail business data using Python, MySQL, SQL, and Power BI. It follows an ETL pipeline to ingest, clean, transform, analyze, and visualize sales data for business insights and future machine learning models.

## Project Architecture

Raw Retail Data (CSV)
        │
        ▼
Python Data Ingestion
        │
        ▼
MySQL Database
        │
        ▼
Data Cleaning & Feature Engineering (Python)
        │
        ▼
SQL Business Analysis
        │
        ▼
Power BI Dashboard
        │
        ▼
Machine Learning Models

## Project Folder Structure

retail_sales_analytics/
│── data/
│   ├── raw/
│   ├── processed/
│
│── sql/
│   ├── schema.sql
│   ├── import_data.sql
│   └── business_queries.sql
│
│── src/
│   ├── config.py
│   ├── utils.py
│   ├── data_ingestion.py
│   ├── data_cleaning.py
│   ├── feature_engineering.py
│   ├── train_model.py
│   ├── evaluate_model.py
│   └── test_mysql_connection.py
│
│── dashboards/
│── models/
│── logs/
│── tests/
│── .env
│── .gitignore
│── requirements.txt
│── README.md
│── main.py


## Setup Steps

1. Clone or download the project.
2. Open the project in Visual Studio Code.
3. Create and activate the Python virtual environment (`.venv`).
4. Install all required libraries using `requirements.txt`.
5. Create the `.env` file with MySQL database credentials and project paths.
6. Verify configuration using `test_config.py`.
7. Verify MySQL connection using `test_mysql_connection.py`.

## Execution Order

1. Configure environment (`.env` and `config.py`).
2. Test MySQL connection.
3. Run Data Ingestion.
4. Run Data Cleaning.
5. Run Feature Engineering.
6. Execute SQL business analysis.
7. Build Power BI dashboard.
8. Train and evaluate Machine Learning model.

## Major Commands

### Create Virtual Environment

python -m venv .venv

### Activate Virtual Environment (Windows)

.venv\Scripts\activate

### Install Required Libraries

pip install -r requirements.txt

### Freeze Installed Libraries

pip freeze > requirements.txt

### Test Configuration

python src/test_config.py

### Test MySQL Connection

python src/test_mysql_connection.py

### Run Logger Test

python src/test_logger.py

## Version Control Conventions

### Git tracks

- Python source files (`src/*.py`)
- SQL scripts (`sql/*.sql`)
- README.md
- requirements.txt
- Power BI dashboard files
- Project documentation

### Git ignores

- `.env`
- `.venv/`
- `logs/`
- `__pycache__/`
- `*.pyc`

### Commit Message Convention

- `feat:` New feature.
- `docs:` Documentation updates.
- `fix:` Bug fixes.
- `refactor:` Code improvements without changing functionality.