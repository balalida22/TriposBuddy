import secrets
import string
from datetime import datetime
from functools import wraps

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.admin import bp
from app.extensions import db, bcrypt
from app.models import (
    User, Invitation, Group, Question, SectionEnum,
    UserQuestionProgress, GroupMembership,
)


def require_root_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_root_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _random_password(length=16):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ─── Dashboard ───────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
@require_root_admin
def index():
    user_count = User.query.count()
    group_count = Group.query.count()
    active_invites = Invitation.query.filter_by(revoked=False, used_by=None).count()
    return render_template(
        'admin/index.html',
        user_count=user_count,
        group_count=group_count,
        active_invites=active_invites,
    )


# ─── Users ───────────────────────────────────────────────────────────────────

@bp.route('/users')
@login_required
@require_root_admin
def users():
    all_users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=all_users)


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@require_root_admin
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_root_admin:
        flash('Cannot reset root admin password here. Use the settings page.', 'error')
        return redirect(url_for('admin.users'))

    temp_password = _random_password()
    user.password_hash = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    db.session.commit()

    flash(
        f'Password for {user.username} reset. Temporary password: {temp_password}',
        'success',
    )
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@require_root_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_root_admin:
        flash('Cannot delete the root admin account.', 'error')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" deleted.', 'info')
    return redirect(url_for('admin.users'))


# ─── Invitations ─────────────────────────────────────────────────────────────

@bp.route('/invites')
@login_required
@require_root_admin
def invites():
    all_invites = Invitation.query.order_by(Invitation.created_at.desc()).all()
    return render_template('admin/invites.html', invites=all_invites)


@bp.route('/invites/generate', methods=['POST'])
@login_required
@require_root_admin
def generate_invite():
    token = secrets.token_urlsafe(32)
    invitation = Invitation(token=token, created_by=current_user.id)
    db.session.add(invitation)
    db.session.commit()

    invite_url = url_for('auth.register', token=token, _external=True)
    flash(f'Invite link: {invite_url}', 'success')
    return redirect(url_for('admin.invites'))


@bp.route('/invites/<int:invite_id>/revoke', methods=['POST'])
@login_required
@require_root_admin
def revoke_invite(invite_id):
    invitation = Invitation.query.get_or_404(invite_id)
    if invitation.used_by:
        flash('Cannot revoke an already-used invite.', 'error')
        return redirect(url_for('admin.invites'))
    invitation.revoked = True
    db.session.commit()
    flash('Invite revoked.', 'info')
    return redirect(url_for('admin.invites'))


# ─── Groups ──────────────────────────────────────────────────────────────────

@bp.route('/groups')
@login_required
@require_root_admin
def groups():
    all_groups = Group.query.order_by(Group.name).all()
    return render_template('admin/groups.html', groups=all_groups)


@bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
@require_root_admin
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    name = group.name
    db.session.delete(group)
    db.session.commit()
    flash(f'Group "{name}" deleted.', 'info')
    return redirect(url_for('admin.groups'))


# ─── Questions ───────────────────────────────────────────────────────────────

@bp.route('/questions')
@login_required
@require_root_admin
def questions():
    sections = [s.value for s in SectionEnum]
    years = list(range(2016, 2026))
    all_questions = (
        Question.query
        .order_by(Question.section, Question.year, Question.question_number)
        .all()
    )
    # Build lookup: (section, year, q_number) → question object
    qmap = {}
    max_q_per_section = {s: 12 for s in sections}
    for q in all_questions:
        qmap[(q.section.value, q.year, q.question_number)] = q
        if q.question_number > max_q_per_section[q.section.value]:
            max_q_per_section[q.section.value] = q.question_number

    return render_template(
        'admin/questions.html',
        qmap=qmap,
        sections=sections,
        years=years,
        max_q_per_section=max_q_per_section,
        section_values=[s.value for s in SectionEnum],
    )


@bp.route('/questions/add', methods=['POST'])
@login_required
@require_root_admin
def add_question():
    section_val = request.form.get('section', '')
    try:
        year = int(request.form.get('year', 0))
        q_num = int(request.form.get('question_number', 0))
    except ValueError:
        flash('Invalid year or question number.', 'error')
        return redirect(url_for('admin.questions'))

    try:
        section = SectionEnum(section_val)
    except ValueError:
        flash('Invalid section.', 'error')
        return redirect(url_for('admin.questions'))

    existing = Question.query.filter_by(
        section=section, year=year, question_number=q_num
    ).first()
    if existing:
        flash('That question already exists.', 'error')
        return redirect(url_for('admin.questions'))

    db.session.add(Question(section=section, year=year, question_number=q_num))
    db.session.commit()
    flash(f'Question {section.value} {year} Q{q_num} added.', 'success')
    return redirect(url_for('admin.questions'))


@bp.route('/questions/<int:q_id>/delete', methods=['POST'])
@login_required
@require_root_admin
def delete_question(q_id):
    q = Question.query.get_or_404(q_id)
    progress_count = UserQuestionProgress.query.filter_by(
        question_id=q_id, solved=True
    ).count()

    confirmed = request.form.get('confirmed') == 'true'
    if progress_count > 0 and not confirmed:
        flash(
            f'Question {q.label} has {progress_count} solve record(s). '
            f'Resubmit with confirmed=true to delete.',
            'warning',
        )
        return redirect(url_for('admin.questions'))

    label = q.label
    db.session.delete(q)
    db.session.commit()
    flash(f'Question "{label}" deleted.', 'info')
    return redirect(url_for('admin.questions'))
