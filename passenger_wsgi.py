import sys
import os

_here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _here)

from dotenv import load_dotenv
load_dotenv(os.path.join(_here, '.env'))

from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix

_app = create_app()
# Fix remote IP, scheme, and host from Apache reverse-proxy headers
_app.wsgi_app = ProxyFix(_app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# FORCE_SCRIPT_NAME (e.g. "/TriposBuddy") injects SCRIPT_NAME so that
# url_for() generates correct absolute URLs when the app runs under a
# sub-path on SRCF. Not needed for local dev — omit from local .env.
_prefix = os.environ.get('FORCE_SCRIPT_NAME', '')
if _prefix:
    _inner = _app.wsgi_app
    def _wsgi_with_prefix(environ, start_response):
        environ['SCRIPT_NAME'] = _prefix
        return _inner(environ, start_response)
    application = _wsgi_with_prefix
else:
    application = _app
