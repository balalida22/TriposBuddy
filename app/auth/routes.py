from datetime import datetime

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm
from app.extensions import db, bcrypt
from app.models import User, Invitation


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tracker.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('tracker.index'))
        flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tracker.index'))

    token = request.args.get('token') or request.form.get('token', '')
    invitation = Invitation.query.filter_by(token=token).first()

    if not invitation or not invitation.is_valid:
        return render_template('auth/invalid_invite.html')

    form = RegisterForm()
    if form.validate_on_submit():
        # Default username to CRSID (part before @) if not changed
        email = form.email.data.lower()
        username = form.username.data.strip()

        user = User(
            email=email,
            username=username,
            password_hash=bcrypt.generate_password_hash(form.password.data).decode('utf-8'),
        )
        db.session.add(user)
        db.session.flush()  # assigns user.id

        # Mark invite as used
        invitation.used_by = user.id
        invitation.used_at = datetime.utcnow()

        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    # Pre-fill username with CRSID from token page if email typed
    return render_template('auth/register.html', form=form, token=token)
