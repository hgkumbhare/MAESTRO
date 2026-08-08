"""Path/setup helper so experiment runners can `import experiments.common...` and
`from src.evals.utils import ...` regardless of where they are launched from.

Usage (top of every run.py):
    from experiments.common.bootstrap import PROJECT_ROOT   # noqa: F401  (side effect: sys.path)
"""
import os
import sys

# experiments/common/bootstrap.py -> project root is two levels up.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
