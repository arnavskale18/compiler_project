"""CodeX Execution Profiler Module.

Provides source-level performance profiling for generated C++17 code using g++.
"""

from .validator import profile_cpp_code

__all__ = ["profile_cpp_code"]
