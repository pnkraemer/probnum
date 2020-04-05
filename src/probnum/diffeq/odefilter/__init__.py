"""
Import convenience functions in conveniencefunctions.py to create an
intuitive, numpy-like interface.

Note
----
Local import, because with a global import this does not seem
to work.
"""

from .ivptofilter import *
from .odefilter import *
from .prior import *