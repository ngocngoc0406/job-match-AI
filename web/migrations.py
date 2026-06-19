import sqlite3
import os
import glob

def run_migrations(db_path, sql_dir=None):
    """
    Runs all .sql migration files in the given sql_dir (or the directory
    containing db_path if sql_dir is not provided).
    Uses 'CREATE TABLE IF NOT EXISTS' style for simplicity.
    """
    if sql_dir is None:
        sql_dir = os.path.dirname(db_path)
    # Ensure the directory containing the DB exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # Find all .sql files and sort them by name (e.g., 000_..., 001_...)
    sql_files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))
    
    if not sql_files:
        print(f"No migration files found in {sql_dir}.")
        return

    print(f"Found {len(sql_files)} migration files.")
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for sql_file in sql_files:
            print(f"Executing {os.path.basename(sql_file)}...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                # Split by semicolon to execute multiple statements if needed
                # although sqlite3.executescript does this automatically
                cursor.executescript(sql_script)
        conn.commit()
        print("Migrations completed successfully.")
    except Exception as e:
        print(f"Error running migrations: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # If run directly, look for app.db in the same/data directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_db = os.path.join(current_dir, 'data', 'app.db')
    run_migrations(target_db)
