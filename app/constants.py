"""
Project-wide constants shared across blueprints.
Update YEARS here when new past-paper years are added.
"""
from app.models import SectionEnum

SECTIONS = [s.value for s in SectionEnum]
YEARS = list(range(2016, 2026))
Q_RANGE = range(1, 13)
