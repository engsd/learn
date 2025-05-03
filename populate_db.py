# 文件名: populate_db.py
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import getpass # To securely get password

# --- Database Configuration ---
# Use the user and database you created
DB_CONFIG = {
    'host': 'localhost',
    'user': 'yunduan',
    'database': 'yunduan1'
    # Password will be asked securely
}

# --- Data Generation Parameters ---
START_DATE = date(2023, 1, 1) # Start date for data generation
END_DATE = date.today()      # End date (today)
CATEGORIES = ['电子产品', '家居用品', '服饰鞋包', '图书音像', '户外运动', '美妆个护']
NUM_ROWS_TARGET = 20000 # Target number of rows to generate

# --- Table Schema ---
TABLE_NAME = 'sales_data'
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL,       -- Changed from 日期 to sale_date (using DATE type)
    category VARCHAR(50) NOT NULL, -- Changed from 类别 to category
    sales_amount DECIMAL(10, 2) NOT NULL, -- Changed from 销售额 to sales_amount (using DECIMAL)
    quantity INT NOT NULL,         -- Changed from 销售数量 to quantity
    INDEX idx_date (sale_date),    -- Add index for faster date filtering
    INDEX idx_category (category)  -- Add index for faster category filtering
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def generate_large_mock_data(start_date, end_date, categories, num_rows):
    """Generates a larger set of mock sales data as a Pandas DataFrame."""
    print(f"Generating approximately {num_rows} rows of mock data...")
    date_range = pd.date_range(start_date, end_date)
    num_days = len(date_range)
    data = []
    rng = np.random.default_rng(42) # Seed for reproducibility

    # Calculate average rows per day needed
    avg_rows_per_day = max(1, int(num_rows / num_days / len(categories)))

    for d in date_range:
        for category in categories:
            # Generate a variable number of entries per day/category
            num_entries_today = rng.integers(max(1, avg_rows_per_day - 2), avg_rows_per_day + 3)
            for _ in range(num_entries_today):
                sales = max(0, int(rng.normal(150, 50))) # Sales amount > 0
                qty = max(1, int(rng.normal(10, 5)))     # Quantity >= 1
                data.append({
                    'sale_date': d.date(), # Store as date object
                    'category': category,
                    'sales_amount': float(sales), # Use float for potential decimals before DB insert
                    'quantity': qty
                })
            if len(data) >= num_rows: # Stop if target reached
                 break
        if len(data) >= num_rows:
             break

    print(f"Generated {len(data)} data points.")
    return pd.DataFrame(data)

def insert_data_to_mysql(df, db_config, table_name):
    """Connects to MySQL and inserts DataFrame data into the specified table."""
    conn = None
    inserted_rows = 0
    # Prompt for password securely
    db_config['password'] = getpass.getpass(f"Enter password for MySQL user '{db_config['user']}': ")

    try:
        print(f"Connecting to database '{db_config['database']}'...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("Connection successful.")

        # Create table if it doesn't exist
        print(f"Checking/Creating table '{table_name}'...")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        print(f"Table '{table_name}' is ready.")

        # Prepare data for insertion (list of tuples)
        data_tuples = [tuple(x) for x in df.to_numpy()]

        # Prepare the SQL INSERT statement
        # Using DataFrame columns assuming they match table columns (excluding id)
        cols = ', '.join(df.columns) # 'sale_date, category, sales_amount, quantity'
        placeholders = ', '.join(['%s'] * len(df.columns)) # '?, ?, ?, ?' for SQLite, '%s, %s, %s, %s' for MySQL
        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

        print(f"Inserting {len(data_tuples)} rows into '{table_name}'. This may take a while...")
        # Use executemany for bulk insert efficiency
        cursor.executemany(sql, data_tuples)
        conn.commit() # Commit the transaction
        inserted_rows = cursor.rowcount
        print(f"Successfully inserted {inserted_rows} rows.")

    except Error as e:
        print(f"Error connecting to or inserting data into MySQL: {e}")
        if conn and conn.is_connected():
            print("Rolling back transaction...")
            conn.rollback()

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection closed.")
    return inserted_rows


if __name__ == "__main__":
    # 1. Generate data
    df_large_data = generate_large_mock_data(START_DATE, END_DATE, CATEGORIES, NUM_ROWS_TARGET)

    # 2. Insert data into MySQL
    if not df_large_data.empty:
        insert_data_to_mysql(df_large_data, DB_CONFIG, TABLE_NAME)
    else:
        print("No data generated to insert.")