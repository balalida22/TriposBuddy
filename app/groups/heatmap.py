from app.extensions import db
from app.models import (
    GroupMembership, UserQuestionProgress, Question, User, SectionEnum
)

SECTIONS = [s.value for s in SectionEnum]
YEARS = list(range(2016, 2026))
Q_RANGE = range(1, 13)


def solve_fill_color(solved_count, total_members, threshold):
    """Linear gradient: white (0%) → green (#22c55e) at threshold."""
    if total_members == 0 or threshold <= 0:
        return 'rgb(255,255,255)'
    ratio = min(solved_count / (total_members * threshold), 1.0)
    # White (255,255,255) → #22c55e (34,197,94)
    r = round(255 + ratio * (34 - 255))
    g = round(255 + ratio * (197 - 255))
    b = round(255 + ratio * (94 - 255))
    return f'rgb({r},{g},{b})'


def compute_heatmap(group, viewer_user):
    """
    Returns nested dict:
      section_name → year → q_number → {
          question_id, fill_color, border_color, solve_count, total_members
      }
    Missing questions (admin-deleted) have value None.
    """
    member_ids = [
        m.user_id for m in GroupMembership.query.filter_by(group_id=group.id).all()
    ]
    total_members = len(member_ids)

    # Solve counts per question within the group
    solve_counts = {}  # question_id → set of user_ids who solved it
    if member_ids:
        records = (
            db.session.query(
                UserQuestionProgress.question_id,
                UserQuestionProgress.user_id,
            )
            .filter(
                UserQuestionProgress.user_id.in_(member_ids),
                UserQuestionProgress.solved.is_(True),
            )
            .all()
        )
        for qid, uid in records:
            solve_counts.setdefault(qid, set()).add(uid)

    # Viewer's own solved set (for border)
    viewer_solved = set()
    if viewer_user and viewer_user.id in member_ids:
        viewer_solved = {
            p.question_id
            for p in UserQuestionProgress.query.filter_by(
                user_id=viewer_user.id, solved=True
            ).all()
        }

    # Build question lookup
    questions = Question.query.all()
    qmap = {
        (q.section.value, q.year, q.question_number): q for q in questions
    }

    heatmap = {}
    for section in SECTIONS:
        heatmap[section] = {}
        for year in YEARS:
            heatmap[section][year] = {}
            for q_num in Q_RANGE:
                q = qmap.get((section, year, q_num))
                if q is None:
                    heatmap[section][year][q_num] = None
                    continue

                count = len(solve_counts.get(q.id, set()))
                fill = solve_fill_color(count, total_members, group.sat_threshold)
                border = '#22c55e' if q.id in viewer_solved else 'transparent'

                heatmap[section][year][q_num] = {
                    'question_id': q.id,
                    'fill_color': fill,
                    'border_color': border,
                    'solve_count': count,
                    'total_members': total_members,
                }

    return heatmap


def get_cell_solvers(group, question_id):
    """Return list of usernames of group members who solved a question."""
    member_ids = [
        m.user_id for m in GroupMembership.query.filter_by(group_id=group.id).all()
    ]
    if not member_ids:
        return []

    solvers = (
        db.session.query(User.username)
        .join(UserQuestionProgress, UserQuestionProgress.user_id == User.id)
        .filter(
            UserQuestionProgress.question_id == question_id,
            UserQuestionProgress.solved.is_(True),
            User.id.in_(member_ids),
        )
        .all()
    )
    return [row.username for row in solvers]
