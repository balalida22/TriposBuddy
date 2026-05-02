from flask import Blueprint

bp = Blueprint('groups', __name__, url_prefix='/groups')

from app.groups import routes  # noqa: E402, F401
