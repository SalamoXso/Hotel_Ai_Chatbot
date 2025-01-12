from flask import Flask
from models import db, Room  # Import Room and db from models.py

app = Flask(__name__)

# Configure the database (replace with your actual database URI)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://username:password@localhost/hotel_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

def populate_rooms():
    """
    Populate the Room table with sample data.
    """
    # Check if rooms already exist to avoid duplicates
    if Room.query.count() == 0:
        rooms = [
            Room(
                room_type="Single Room",
                description="A cozy single room with a queen-sized bed.",
                price_per_night=100,
                max_guests=1,
                amenities="WiFi, AC, TV"
            ),
            Room(
                room_type="Double Room",
                description="A spacious double room with two queen-sized beds.",
                price_per_night=150,
                max_guests=2,
                amenities="WiFi, AC, TV, Mini Fridge"
            ),
            Room(
                room_type="Suite",
                description="A luxurious suite with a king-sized bed and a living area.",
                price_per_night=250,
                max_guests=4,
                amenities="WiFi, AC, TV, Mini Bar, Jacuzzi"
            )
        ]
        db.session.bulk_save_objects(rooms)
        db.session.commit()
        print("Rooms populated successfully!")
    else:
        print("Rooms already exist in the database.")

if __name__ == "__main__":
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Populate rooms only if the table is empty
        populate_rooms()
    
    # Run the Flask app
    app.run(debug=True)