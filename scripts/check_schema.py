"""Check actual database schema for contacts table"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Parse DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "")
    # Format: mysql+pymysql://user:password@host:port/dbname
    parts = db_url.replace("mysql+pymysql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")
    
    connection = pymysql.connect(
        host=host_port[0],
        port=int(host_port[1]) if len(host_port) > 1 else 3306,
        user=user_pass[0],
        password=user_pass[1],
        database=host_port_db[1],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        # Get contacts table schema
        cursor.execute("SHOW CREATE TABLE contacts")
        result = cursor.fetchone()
        print("=== CONTACTS TABLE SCHEMA ===")
        print(result['Create Table'])
        print("\n")
        
        # Get jewellers table schema
        cursor.execute("SHOW CREATE TABLE jewellers")
        result = cursor.fetchone()
        print("=== JEWELLERS TABLE SCHEMA ===")
        print(result['Create Table'])
        
    connection.close()
    print("\n✅ Schema check complete")
    
except Exception as e:
    print(f"❌ Failed to check schema: {e}")
