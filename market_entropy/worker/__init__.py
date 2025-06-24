# market_entropy/worker/__init__.py
from .tasks import celery_app

__all__ = ['celery_app']