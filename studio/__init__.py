"""
Duino API — studio/__init__.py
Exposes the start() function used by notebooks.
"""
from studio.backend.colab import start

__all__ = ["start"]
