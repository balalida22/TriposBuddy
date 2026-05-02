from flask import render_template, abort
from flask_login import login_required, current_user

from app.notifications import bp
from app.extensions import db
from app.models import Notification


@bp.route('/poll')
@login_required
def poll():
    """HTMX partial: return unread notifications as banner HTML."""
    unread = (
        Notification.query
        .filter_by(user_id=current_user.id, read=False)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template('notifications/_banner.html', notifications=unread)


@bp.route('/<int:notif_id>/dismiss', methods=['POST'])
@login_required
def dismiss(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)
    notif.read = True
    db.session.commit()
    return '', 204
