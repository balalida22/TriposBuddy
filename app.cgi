#!/usr/bin/python3
"""CGI entry point for SRCF deployment.

Apache executes this script directly on the web server, which reads the code
from the NFS-mounted home directory. No socket or cross-host connectivity
needed. The venv's site-packages are added to sys.path manually because the
shebang uses the system python3 (not the venv symlink) for portability.
"""
import sys
import os
import glob

# Resolve project root from this script's location (works on any SRCF host)
_here = os.path.dirname(os.path.abspath(__file__))

# Add venv site-packages so system python3 can import Flask et al.
for _sp in sorted(glob.glob(os.path.join(_here, 'venv', 'lib', 'python*', 'site-packages'))):
    sys.path.insert(0, _sp)

sys.path.insert(0, _here)
os.chdir(_here)

# passenger_wsgi handles .env loading and builds the WSGI app chain
# (includes FORCE_SCRIPT_NAME middleware for /TriposBuddy prefix)
from passenger_wsgi import application  # noqa: E402
from wsgiref.handlers import CGIHandler  # noqa: E402

CGIHandler().run(application)
