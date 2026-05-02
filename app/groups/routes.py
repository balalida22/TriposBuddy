import re
from datetime import datetime
from functools import wraps

from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user

from app.groups import bp
from app.groups.heatmap import compute_heatmap, get_cell_solvers, SECTIONS, YEARS, Q_RANGE
from app.extensions import db
from app.models import (
    Group, GroupMembership, GroupJoinRequest, Notification,
    MemberRole, JoinRequestStatus, Question, User,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _generate_slug(name):
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')[:80]
    base = slug
    counter = 1
    while Group.query.filter_by(slug=slug).first():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def _get_membership(group):
    return GroupMembership.query.filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()


def _require_group_admin(f):
    @wraps(f)
    def decorated(slug, *args, **kwargs):
        group = Group.query.filter_by(slug=slug).first_or_404()
        membership = _get_membership(group)
        if not membership or membership.role != MemberRole.admin:
            abort(403)
        return f(slug, *args, group=group, membership=membership, **kwargs)
    return decorated


def _notify(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


# ─── My Groups ──────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def my_groups():
    memberships = (
        GroupMembership.query
        .filter_by(user_id=current_user.id)
        .join(Group, Group.id == GroupMembership.group_id)
        .order_by(Group.name)
        .all()
    )
    return render_template('groups/my_groups.html', memberships=memberships)


# ─── Discover ───────────────────────────────────────────────────────────────

@bp.route('/discover')
@login_required
def discover():
    public_groups = Group.query.filter_by(is_public=True).order_by(Group.name).all()
    my_group_ids = {
        m.group_id
        for m in GroupMembership.query.filter_by(user_id=current_user.id).all()
    }
    pending_ids = {
        r.group_id
        for r in GroupJoinRequest.query.filter_by(
            user_id=current_user.id, status=JoinRequestStatus.pending
        ).all()
    }
    return render_template(
        'groups/discover.html',
        groups=public_groups,
        my_group_ids=my_group_ids,
        pending_ids=pending_ids,
    )


# ─── Create ─────────────────────────────────────────────────────────────────

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = 'is_public' in request.form
        auto_approve = 'auto_approve' in request.form
        try:
            threshold = float(request.form.get('sat_threshold', 0.667))
            threshold = max(0.01, min(1.0, threshold))
        except ValueError:
            threshold = 0.667

        if not name:
            flash('Group name is required.', 'error')
            return render_template('groups/create.html')

        slug = _generate_slug(name)
        group = Group(
            name=name,
            slug=slug,
            description=description or None,
            is_public=is_public,
            auto_approve=auto_approve,
            sat_threshold=threshold,
            created_by=current_user.id,
        )
        db.session.add(group)
        db.session.flush()

        membership = GroupMembership(
            group_id=group.id,
            user_id=current_user.id,
            role=MemberRole.admin,
        )
        db.session.add(membership)
        db.session.commit()

        flash(f'Group "{name}" created.', 'success')
        return redirect(url_for('groups.group_page', slug=slug))

    return render_template('groups/create.html')


# ─── Group page (auto-switch: public view vs member view) ───────────────────

@bp.route('/<slug>')
@login_required
def group_page(slug):
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = _get_membership(group)

    if membership:
        # Member view: show heatmap
        heatmap = compute_heatmap(group, current_user)
        members = (
            GroupMembership.query
            .filter_by(group_id=group.id)
            .join(User, User.id == GroupMembership.user_id)
            .order_by(User.username)
            .all()
        )
        pending_count = GroupJoinRequest.query.filter_by(
            group_id=group.id, status=JoinRequestStatus.pending
        ).count()
        return render_template(
            'groups/group_member.html',
            group=group,
            membership=membership,
            heatmap=heatmap,
            sections=SECTIONS,
            years=YEARS,
            q_range=Q_RANGE,
            members=members,
            pending_count=pending_count,
        )

    # Public/pre-join view
    pending_request = GroupJoinRequest.query.filter_by(
        group_id=group.id,
        user_id=current_user.id,
        status=JoinRequestStatus.pending,
    ).first()
    return render_template(
        'groups/group_public.html',
        group=group,
        pending_request=pending_request,
    )


# ─── Join ───────────────────────────────────────────────────────────────────

@bp.route('/<slug>/join', methods=['POST'])
@login_required
def join(slug):
    group = Group.query.filter_by(slug=slug).first_or_404()

    if _get_membership(group):
        flash('You are already a member of this group.', 'info')
        return redirect(url_for('groups.group_page', slug=slug))

    # Cancel if already has a pending request
    existing = GroupJoinRequest.query.filter_by(
        group_id=group.id,
        user_id=current_user.id,
        status=JoinRequestStatus.pending,
    ).first()
    if existing:
        flash('You already have a pending join request.', 'info')
        return redirect(url_for('groups.group_page', slug=slug))

    if group.auto_approve:
        membership = GroupMembership(
            group_id=group.id,
            user_id=current_user.id,
            role=MemberRole.member,
        )
        db.session.add(membership)
        _notify(current_user.id, f'You have joined "{group.name}".')
        db.session.commit()
        flash(f'You have joined "{group.name}".', 'success')
    else:
        join_request = GroupJoinRequest(
            group_id=group.id,
            user_id=current_user.id,
        )
        db.session.add(join_request)
        db.session.commit()
        flash('Join request sent. Waiting for approval.', 'info')

    return redirect(url_for('groups.group_page', slug=slug))


# ─── Leave ──────────────────────────────────────────────────────────────────

@bp.route('/<slug>/leave', methods=['POST'])
@login_required
def leave(slug):
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = _get_membership(group)
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('groups.group_page', slug=slug))

    is_last_admin = (
        membership.role == MemberRole.admin
        and group.admin_count == 1
    )

    confirm = request.form.get('confirm_delete') == 'true'

    if is_last_admin and not confirm:
        # Show warning page before deleting
        return render_template(
            'groups/leave_warning.html',
            group=group,
        )

    if is_last_admin and confirm:
        db.session.delete(group)
        db.session.commit()
        flash(f'Group "{group.name}" has been deleted.', 'info')
        return redirect(url_for('groups.my_groups'))

    db.session.delete(membership)
    db.session.commit()
    flash(f'You have left "{group.name}".', 'info')
    return redirect(url_for('groups.my_groups'))


# ─── Group Settings ─────────────────────────────────────────────────────────

@bp.route('/<slug>/settings', methods=['GET', 'POST'])
@login_required
@_require_group_admin
def settings(slug, group, membership):
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = 'is_public' in request.form
        auto_approve = 'auto_approve' in request.form
        try:
            threshold = float(request.form.get('sat_threshold', group.sat_threshold))
            threshold = max(0.01, min(1.0, threshold))
        except ValueError:
            threshold = group.sat_threshold

        if not name:
            flash('Group name is required.', 'error')
            return render_template('groups/group_settings.html', group=group)

        # If slug needs to change (name changed)
        if name != group.name:
            new_slug = _generate_slug(name)
            group.slug = new_slug

        group.name = name
        group.description = description or None
        group.is_public = is_public
        group.auto_approve = auto_approve
        group.sat_threshold = threshold
        db.session.commit()

        flash('Group settings updated.', 'success')
        return redirect(url_for('groups.group_page', slug=group.slug))

    return render_template('groups/group_settings.html', group=group)


# ─── Join Requests ───────────────────────────────────────────────────────────

@bp.route('/<slug>/requests')
@login_required
@_require_group_admin
def join_requests(slug, group, membership):
    pending = GroupJoinRequest.query.filter_by(
        group_id=group.id, status=JoinRequestStatus.pending
    ).all()
    return render_template('groups/join_requests.html', group=group, requests=pending)


@bp.route('/<slug>/requests/<int:req_id>/approve', methods=['POST'])
@login_required
@_require_group_admin
def approve_request(slug, req_id, group, membership):
    req = GroupJoinRequest.query.get_or_404(req_id)
    if req.group_id != group.id:
        abort(403)

    req.status = JoinRequestStatus.approved
    req.resolved_at = datetime.utcnow()
    req.resolved_by = current_user.id

    new_membership = GroupMembership(
        group_id=group.id,
        user_id=req.user_id,
        role=MemberRole.member,
    )
    db.session.add(new_membership)
    _notify(req.user_id, f'Your request to join "{group.name}" has been approved.')
    db.session.commit()

    flash('Request approved.', 'success')
    return redirect(url_for('groups.join_requests', slug=slug))


@bp.route('/<slug>/requests/<int:req_id>/reject', methods=['POST'])
@login_required
@_require_group_admin
def reject_request(slug, req_id, group, membership):
    req = GroupJoinRequest.query.get_or_404(req_id)
    if req.group_id != group.id:
        abort(403)

    req.status = JoinRequestStatus.rejected
    req.resolved_at = datetime.utcnow()
    req.resolved_by = current_user.id
    db.session.commit()

    flash('Request rejected.', 'info')
    return redirect(url_for('groups.join_requests', slug=slug))


# ─── Member Management ───────────────────────────────────────────────────────

@bp.route('/<slug>/members/<int:user_id>/promote', methods=['POST'])
@login_required
@_require_group_admin
def promote_member(slug, user_id, group, membership):
    target = GroupMembership.query.filter_by(
        group_id=group.id, user_id=user_id
    ).first_or_404()
    target.role = MemberRole.admin
    db.session.commit()
    flash('Member promoted to admin.', 'success')
    return redirect(url_for('groups.group_page', slug=slug))


@bp.route('/<slug>/members/<int:user_id>/demote', methods=['POST'])
@login_required
@_require_group_admin
def demote_member(slug, user_id, group, membership):
    target = GroupMembership.query.filter_by(
        group_id=group.id, user_id=user_id
    ).first_or_404()
    if target.user_id == current_user.id:
        flash('You cannot demote yourself. Transfer admin first.', 'error')
        return redirect(url_for('groups.group_page', slug=slug))
    if group.admin_count <= 1:
        flash('Cannot demote the only admin.', 'error')
        return redirect(url_for('groups.group_page', slug=slug))
    target.role = MemberRole.member
    db.session.commit()
    flash('Admin demoted to member.', 'info')
    return redirect(url_for('groups.group_page', slug=slug))


@bp.route('/<slug>/members/<int:user_id>/remove', methods=['POST'])
@login_required
@_require_group_admin
def remove_member(slug, user_id, group, membership):
    if user_id == current_user.id:
        flash('Use "Leave Group" to remove yourself.', 'error')
        return redirect(url_for('groups.group_page', slug=slug))
    target = GroupMembership.query.filter_by(
        group_id=group.id, user_id=user_id
    ).first_or_404()
    db.session.delete(target)
    db.session.commit()
    flash('Member removed from group.', 'info')
    return redirect(url_for('groups.group_page', slug=slug))


# ─── Heatmap HTMX partials ───────────────────────────────────────────────────

@bp.route('/<slug>/heatmap/cell/<int:question_id>/solvers')
@login_required
def cell_solvers(slug, question_id):
    group = Group.query.filter_by(slug=slug).first_or_404()
    if not _get_membership(group):
        abort(403)
    solvers = get_cell_solvers(group, question_id)
    q = Question.query.get_or_404(question_id)
    return render_template(
        'groups/_tooltip.html',
        solvers=solvers,
        question_label=q.label,
    )
