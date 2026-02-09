import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/bok_analyzer.db")

try:
    if not DB_PATH.exists():
        print(f"Error: Database file not found at {DB_PATH}")
        exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keywords")
    count = cursor.fetchone()[0]
    print(f"Keyword Count: {count}")
    
    cursor.execute("SELECT term, polarity, base_weight FROM keywords LIMIT 5")
    rows = cursor.fetchall()
    print("Sample Keywords:")
    for row in rows:
        print(row)

    conn.close()
except Exception as e:
    print(f"Error: {e}")
