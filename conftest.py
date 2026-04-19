"""Add src/ to sys.path so test files can import src modules directly."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
