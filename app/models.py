from datetime import datetime
from flask_login import UserMixin
from app import db
from sqlalchemy import UniqueConstraint

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_tutor = db.Column(db.Boolean, default=False)
    subjects = db.Column(db.String(200))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200), default='default.jpg')

    # Связи
    offers = db.relationship('TutoringOffer', backref='tutor', lazy=True, cascade='all, delete-orphan')
    
    # Бронирования
    bookings_as_student = db.relationship('Booking', foreign_keys='Booking.student_id', backref='student', lazy=True)
    bookings_as_tutor = db.relationship('Booking', foreign_keys='Booking.tutor_id', backref='tutor', lazy=True)
    
    # Чат
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)
    
    # Отзывы
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer', lazy=True)
    reviews_received = db.relationship('Review', foreign_keys='Review.tutor_id', backref='tutor', lazy=True)

    @property
    def average_rating(self):
        reviews = [r.rating for r in self.reviews_received]
        return round(sum(reviews) / len(reviews), 1) if reviews else 0


class TutoringOffer(db.Model):
    __tablename__ = 'tutoring_offer'
    id = db.Column(db.String(100), primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offer_id = db.Column(db.String(100), db.ForeignKey('tutoring_offer.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    offer = db.relationship('TutoringOffer', backref='bookings', lazy=True)


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Оценка от 1 до 5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('reviewer_id', 'booking_id', name='one_review_per_booking'),)