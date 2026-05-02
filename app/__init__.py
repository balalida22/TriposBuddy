import os
import click

from flask import Flask, redirect, url_for
from flask_login import current_user

from app.config import config
from app.extensions import db, migrate, login_manager, bcrypt, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # User loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.tracker import bp as tracker_bp
    app.register_blueprint(tracker_bp)

    from app.groups import bp as groups_bp
    app.register_blueprint(groups_bp)

    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.notifications import bp as notifications_bp
    app.register_blueprint(notifications_bp)

    # Root redirect
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('tracker.index'))
        return redirect(url_for('auth.login'))

    # CLI commands
    _register_cli(app)

    return app


def _register_cli(app):
    @app.cli.command('seed-questions')
    def seed_questions():
        """Populate all default questions (4 sections × 10 years × 12 questions)."""
        from app.models import Question, SectionEnum

        sections = list(SectionEnum)
        years = range(2016, 2026)

        # Fetch all existing (section, year, question_number) tuples in one query
        existing = {
            (q.section, q.year, q.question_number)
            for q in Question.query.with_entities(
                Question.section, Question.year, Question.question_number
            ).all()
        }

        new_questions = [
            Question(section=section, year=year, question_number=q_num)
            for section in sections
            for year in years
            for q_num in range(1, 13)
            if (section, year, q_num) not in existing
        ]
        db.session.add_all(new_questions)
        db.session.commit()
        click.echo(f'Seeded {len(new_questions)} questions.')

    @app.cli.command('create-admin')
    @click.argument('email')
    @click.argument('username')
    @click.argument('password')
    def create_admin(email, username, password):
        """Create the root admin user. Usage: flask create-admin EMAIL USERNAME PASSWORD"""
        from app.models import User

        if not email.endswith('@cam.ac.uk'):
            click.echo('Error: email must be a @cam.ac.uk address.')
            return

        if User.query.filter_by(is_root_admin=True).first():
            click.echo('Error: a root admin already exists.')
            return

        if User.query.filter_by(email=email).first():
            click.echo('Error: email already registered.')
            return

        user = User(
            email=email,
            username=username,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            is_root_admin=True,
        )
        db.session.add(user)
        db.session.commit()
        click.echo(f'Root admin created: {username} ({email})')
