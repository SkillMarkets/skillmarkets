from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User, TutoringOffer, Booking, Message, Review
from app.forms import LoginForm, RegisterForm, TutoringOfferForm, BookingForm
import secrets
from datetime import timedelta
import stripe
from config import Config

# Инициализация Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

# Главная страница
@main.route('/')
def index():
    tutors = User.query.filter_by(is_tutor=True).all()
    return render_template('index.html', tutors=tutors)

# Профиль
@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Публикация услуги
@main.route('/offer/new', methods=['GET', 'POST'])
@login_required
def new_offer():
    if not current_user.is_tutor:
        flash('Только репетиторы могут публиковать услуги.', 'warning')
        return redirect(url_for('main.index'))
    
    form = TutoringOfferForm()
    if form.validate_on_submit():
        offer_id = secrets.token_urlsafe(16)
        offer = TutoringOffer(
            id=offer_id,
            title=form.title.data,
            description=form.description.data,
            subject=form.subject.data,
            price_per_hour=form.price_per_hour.data,
            user_id=current_user.id
        )
        db.session.add(offer)
        db.session.commit()
        flash('Ваша услуга опубликована!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('new_offer.html', form=form)

# Просмотр услуги
@main.route('/offer/<offer_id>')
def view_offer(offer_id):
    offer = TutoringOffer.query.get_or_404(offer_id)
    return render_template('view_offer.html', offer=offer)

# Поиск по предмету
@main.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if query:
        offers = TutoringOffer.query.filter(
            TutoringOffer.subject.ilike(f'%{query}%')
        ).all()
    else:
        offers = []
    return render_template('search_results.html', offers=offers, query=query)

# Бронирование
@main.route('/book/<offer_id>', methods=['GET', 'POST'])
@login_required
def book_tutor(offer_id):
    offer = TutoringOffer.query.get_or_404(offer_id)
    if offer.user_id == current_user.id:
        flash("Вы не можете бронировать самого себя!", "danger")
        return redirect(url_for('main.view_offer', offer_id=offer_id))
    if current_user.is_tutor:
        flash("Только студенты могут бронировать занятия.", "warning")
        return redirect(url_for('main.view_offer', offer_id=offer_id))

    form = BookingForm()
    if form.validate_on_submit():
        start = form.start_time.data
        duration = form.duration_hours.data
        end = start + timedelta(hours=duration)

        booking = Booking(
            student_id=current_user.id,
            tutor_id=offer.user_id,
            offer_id=offer.id,
            start_time=start,
            end_time=end
        )
        db.session.add(booking)
        db.session.commit()
        flash("Бронирование создано! Ожидайте подтверждения от репетитора.", "success")
        return redirect(url_for('main.profile'))

    return render_template('book_tutor.html', form=form, offer=offer)

# Чат
@main.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).limit(50).all()
    return render_template('chat.html', other=other, messages=messages)

@main.route('/send_message/<int:user_id>', methods=['POST'])
@login_required
def send_message(user_id):
    content = request.form.get('content', '').strip()
    if content and len(content) <= 1000:
        msg = Message(
            sender_id=current_user.id,
            recipient_id=user_id,
            content=content
        )
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('main.chat', user_id=user_id))

# --- ПЛАТЕЖИ (STRIPE) ---
@main.route('/pay/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def pay_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id != current_user.id:
        flash("Вы не можете оплатить чужое бронирование.", "danger")
        return redirect(url_for('main.index'))
    if booking.status != 'pending':
        flash("Это бронирование уже оплачено или отменено.", "warning")
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        try:
            amount = int(booking.offer.price_per_hour * 100)  # в центах
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                metadata={'booking_id': booking_id}
            )
            return jsonify({'client_secret': intent['client_secret']})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    return render_template('pay_booking.html', booking=booking, stripe_public_key=Config.STRIPE_PUBLIC_KEY)

# --- ОТЗЫВЫ ---
@main.route('/review/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def leave_review(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id != current_user.id:
        flash("Вы не можете оставить отзыв.", "danger")
        return redirect(url_for('main.index'))
    if booking.status != 'completed':
        flash("Можно оставить отзыв только после завершения занятия.", "warning")
        return redirect(url_for('main.profile'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '')
        # Проверка: отзыв уже есть?
        existing = Review.query.filter_by(reviewer_id=current_user.id, booking_id=booking_id).first()
        if existing:
            flash("Вы уже оставили отзыв.", "warning")
        else:
            review = Review(
                reviewer_id=current_user.id,
                tutor_id=booking.tutor_id,
                booking_id=booking_id,
                rating=rating,
                comment=comment
            )
            db.session.add(review)
            db.session.commit()
            flash("Спасибо за отзыв!", "success")
        return redirect(url_for('main.profile'))

    return render_template('review.html', booking=booking)

# --- АУТЕНТИФИКАЦИЯ ---
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Вы вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Неверный email или пароль', 'danger')
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Имя пользователя уже занято', 'danger')
            return render_template('register.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email уже зарегистрирован', 'danger')
            return render_template('register.html', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            is_tutor=form.is_tutor.data
        )
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))