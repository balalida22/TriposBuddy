from flask import render_template, request, flash, redirect, url_for, make_response
from flask_login import login_required, current_user

from app.settings import bp
from app.extensions import db, bcrypt
from app.models import User


@bp.route('/', methods=['GET'])
@login_required
def index():
    return render_template('settings/index.html')


@bp.route('/profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username', '').strip()

    if not username:
        flash('Username cannot be empty.', 'error')
        return redirect(url_for('settings.index'))

    if len(username) > 50:
        flash('Username must be 50 characters or fewer.', 'error')
        return redirect(url_for('settings.index'))

    existing = User.query.filter_by(username=username).first()
    if existing and existing.id != current_user.id:
        flash('That username is already taken.', 'error')
        return redirect(url_for('settings.index'))

    current_user.username = username
    db.session.commit()
    flash('Username updated.', 'success')
    return redirect(url_for('settings.index'))


@bp.route('/password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('settings.index'))

    if len(new_pw) < 8:
        flash('New password must be at least 8 characters.', 'error')
        return redirect(url_for('settings.index'))

    if new_pw != confirm_pw:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('settings.index'))

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    flash('Password updated.', 'success')
    return redirect(url_for('settings.index'))


@bp.route('/darkmode', methods=['POST'])
@login_required
def toggle_darkmode():
    current_user.dark_mode = not current_user.dark_mode
    db.session.commit()
    # Return a tiny response; the page JS reloads to apply the theme
    return redirect(url_for('settings.index'))
