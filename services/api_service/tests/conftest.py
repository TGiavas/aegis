"""
Pytest configuration and fixtures.

Fixtures are reusable test setup/teardown functions.
They're automatically discovered by pytest from this file.
"""

import pytest


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================
# This tells pytest to use asyncio for async tests

pytest_plugins = ["pytest_asyncio"]


# =============================================================================
# FIXTURES (will be expanded later)
# =============================================================================
# Fixtures provide test dependencies. Example usage:
#
#   def test_something(my_fixture):
#       # my_fixture is automatically provided
#
# We'll add database fixtures once we have models set up.

