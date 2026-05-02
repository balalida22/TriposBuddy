import sys
import os

_here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _here)

from dotenv import load_dotenv
load_dotenv(os.path.join(_here, '.env'))

from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix

_app = create_app()
# Fix SCRIPT_NAME / scheme / host when running behind Apache mod_proxy
_app.wsgi_app = ProxyFix(_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
application = _app
