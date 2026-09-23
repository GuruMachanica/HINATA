"""Mood feature — persistent temperament with time-based decay."""
from .decay import MoodDecayEngine
from .feature import MoodFeature

__all__ = ["MoodDecayEngine", "MoodFeature"]
