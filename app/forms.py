from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    TextAreaField, FloatField, DateTimeLocalField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(), EqualTo('password', message='Пароли должны совпадать')
    ])
    is_tutor = BooleanField('Хочу стать репетитором')
    submit = SubmitField('Зарегистрироваться')

class TutoringOfferForm(FlaskForm):
    title = StringField('Название услуги', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    subject = StringField('Предмет', validators=[DataRequired(), Length(max=100)])
    price_per_hour = FloatField('Цена за час ($)', validators=[DataRequired()])
    submit = SubmitField('Опубликовать услугу')

class BookingForm(FlaskForm):
    start_time = DateTimeLocalField('Начало занятия', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duration_hours = FloatField('Длительность (часы)', validators=[
        DataRequired(),
        NumberRange(min=0.5, max=10, message='Длительность должна быть от 0.5 до 10 часов')
    ])
    submit = SubmitField('Забронировать')