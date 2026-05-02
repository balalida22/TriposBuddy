from datetime import datetime

from flask import render_template, request, abort
from flask_login import login_required, current_user

from app.tracker import bp
from app.extensions import db
from app.models import Question, UserQuestionProgress
from app.constants import SECTIONS, YEARS, Q_RANGE


def _build_tracker_data(solved_ids, question_map):
    """Return nested structure: section → rows (q_num) → cells (year)."""
    max_q = max((k[2] for k in question_map), default=max(Q_RANGE))
    q_range = range(1, max_q + 1)
    sections_data = []
    for section in SECTIONS:
        rows = []
        for q_num in q_range:
            cells = []
            for year in YEARS:
                q = question_map.get((section, year, q_num))
                cells.append({
                    'q': q,
                    'solved': q is not None and q.id in solved_ids,
                })
            rows.append({'q_num': q_num, 'cells': cells})
        sections_data.append({'name': section, 'rows': rows})
    return sections_data


@bp.route('/')
@login_required
def index():
    questions = Question.query.all()
    question_map = {
        (q.section.value, q.year, q.question_number): q for q in questions
    }

    solved_ids = {
        p.question_id
        for p in UserQuestionProgress.query.filter_by(
            user_id=current_user.id, solved=True
        ).all()
    }

    sections_data = _build_tracker_data(solved_ids, question_map)

    return render_template(
        'tracker/index.html',
        sections_data=sections_data,
        years=YEARS,
    )


@bp.route('/toggle', methods=['POST'])
@login_required
def toggle():
    question_id = request.form.get('question_id', type=int)
    if not question_id:
        abort(400)

    q = Question.query.get_or_404(question_id)

    progress = UserQuestionProgress.query.filter_by(
        user_id=current_user.id, question_id=question_id
    ).first()

    if progress is None:
        progress = UserQuestionProgress(
            user_id=current_user.id,
            question_id=question_id,
            solved=True,
            solved_at=datetime.utcnow(),
        )
        db.session.add(progress)
        solved = True
    else:
        progress.solved = not progress.solved
        progress.solved_at = datetime.utcnow() if progress.solved else None
        solved = progress.solved

    db.session.commit()

    return render_template('tracker/_cell.html', cell={'q': q, 'solved': solved})
