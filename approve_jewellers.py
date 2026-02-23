"""
Approve all jewellers in the database
"""
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:postgres@localhost:5432/ektola_db')
conn = engine.connect()

try:
    # Update all jewellers to approved
    result = conn.execute(text("""
        UPDATE jewellers 
        SET is_approved = true, is_active = true
        WHERE is_approved = false
    """))
    
    conn.commit()
    
    # Get count of all jewellers
    count = conn.execute(text("SELECT COUNT(*) FROM jewellers WHERE is_approved = true")).fetchone()[0]
    
    print(f"✅ Successfully approved {result.rowcount} jeweller(s)")
    print(f"📊 Total approved jewellers: {count}")
    
    # Show details
    jewellers = conn.execute(text("""
        SELECT j.id, j.business_name, j.phone_number, u.email, j.is_approved, j.is_active
        FROM jewellers j
        JOIN users u ON j.user_id = u.id
        ORDER BY j.id
    """)).fetchall()
    
    if jewellers:
        print("\n📋 Jeweller List:")
        print("-" * 80)
        for j in jewellers:
            status = "✅ APPROVED" if j[4] and j[5] else "❌ PENDING"
            print(f"ID: {j[0]} | {j[1]} | {j[2]} | {j[3]} | {status}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    conn.rollback()
finally:
    conn.close()
