import sys
import os

# Ensure the project root is on the path regardless of how Passenger sets __file__
_here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _here)

# Load .env if present (must happen before create_app reads os.environ)
from dotenv import load_dotenv
load_dotenv(os.path.join(_here, '.env'))

from app import create_app
application = create_app()
