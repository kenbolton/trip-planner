# tests/test_runner.py
import pytest
import sys
import os

# Add the parent directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_tests():
    """Run all tests with coverage reporting"""
    return pytest.main([
        '-v',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--cov-exclude=tests/*',
        'tests/'
    ])

if __name__ == '__main__':
    sys.exit(run_tests())
