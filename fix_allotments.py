from app import db, Allotment

# Start Flask app context so SQLAlchemy works
from app import app
with app.app_context():
    # Delete all allotments where item_id is NULL
    deleted_count = Allotment.query.filter(Allotment.item_id == None).delete()
    db.session.commit()
    print(f"Deleted {deleted_count} allotment(s) with NULL item_id")
remaining = Allotment.query.filter(Allotment.item_id == None).all()
print("Remaining problematic rows:", remaining)
