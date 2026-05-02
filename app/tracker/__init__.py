from flask import Blueprint

bp = Blueprint('tracker', __name__, url_prefix='/tracker')

from app.tracker import routes  # noqa: E402, F401
