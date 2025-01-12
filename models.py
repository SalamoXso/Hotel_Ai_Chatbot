from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, Text

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    preferred_hotel_chain = db.Column(db.String(100), nullable=True)  # New field
    loyalty_points = db.Column(db.Integer, default=0)  # New field
    conversations = db.relationship('Conversation', back_populates='user', lazy=True)
    memories = db.relationship('Memory', back_populates='user', lazy=True)
    follow_ups = db.relationship('FollowUp', back_populates='user', lazy=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'", name='valid_email'),
        CheckConstraint("LENGTH(username) >= 3", name='username_min_length'),
        CheckConstraint("LENGTH(password) >= 8", name='password_min_length'),
    )

    def __repr__(self):
        return f'<User {self.username}>'

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.String(2000), nullable=False)
    response = db.Column(Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    follow_up_date = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', back_populates='conversations')

    __table_args__ = (
        Index('idx_conversation_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<Conversation {self.id}>'

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False)  # e.g., "preferred_room_type", "frequent_destination"
    value = db.Column(db.String(500), nullable=False)  # e.g., "suite", "New York"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='memories')

    __table_args__ = (
        Index('idx_memory_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<Memory {self.key}: {self.value}>'

class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.String(1000), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='scheduled')  # e.g., "scheduled", "sent", "failed"

    user = db.relationship('User', back_populates='follow_ups')

    __table_args__ = (
        Index('idx_follow_up_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<FollowUp {self.id}>'
    

# Add this to models.py
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(100), nullable=False)  # e.g., "Single", "Double", "Suite"
    description = db.Column(db.String(500), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)  # True if available
    max_guests = db.Column(db.Integer, nullable=False)
    amenities = db.Column(db.String(500), nullable=False)  # e.g., "WiFi, AC, TV"

    def __repr__(self):
        return f'<Room {self.room_type}>'

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in_date = db.Column(db.DateTime, nullable=False)
    check_out_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="confirmed")  # e.g., "confirmed", "cancelled"

    user = db.relationship('User', backref='reservations')
    room = db.relationship('Room', backref='reservations')

    def __repr__(self):
        return f'<Reservation {self.id}>'    