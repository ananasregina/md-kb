#!/usr/bin/env python3
"""
Test script to verify logging configuration.
This script can be run manually to test the logging setup.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from md_kb.config import Config
    from md_kb.__main__ import setup_logging

    # Test config methods
    print("Testing configuration...")
    config = Config()

    log_file = config.get_log_file()
    log_level = config.get_log_level()
    console_level = config.get_log_level_console()
    max_bytes = config.get_log_max_bytes()
    backup_count = config.get_log_backup_count()

    print(f"  Log file: {log_file}")
    print(f"  File log level: {log_level}")
    print(f"  Console log level: {console_level}")
    print(f"  Max bytes: {max_bytes}")
    print(f"  Backup count: {backup_count}")

    # Test logging setup
    print("\nTesting logging setup...")
    setup_logging()

    # Get the root logger
    root_logger = logging.getLogger()
    print(f"  Root logger level: {root_logger.level}")
    print(f"  Number of handlers: {len(root_logger.handlers)}")

    # Verify handlers
    file_handler = None
    console_handler = None

    for handler in root_logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            file_handler = handler
            print(f"  File handler found - Level: {handler.level}, MaxBytes: {handler.maxBytes}, BackupCount: {handler.backupCount}")
        elif isinstance(handler, logging.StreamHandler):
            console_handler = handler
            print(f"  Console handler found - Level: {handler.level}")

    if file_handler and console_handler:
        print("\n✓ Both file and console handlers configured successfully!")
    else:
        print("\n✗ ERROR: Missing file or console handler")
        sys.exit(1)

    # Test logging output
    print("\nTesting log output...")
    test_logger = logging.getLogger(__name__)
    test_logger.debug("This is a DEBUG message (should only appear in file)")
    test_logger.info("This is an INFO message (should only appear in file)")
    test_logger.warning("This is a WARNING message (should appear in both)")
    test_logger.error("This is an ERROR message (should appear in both)")

    print(f"✓ Logs written to: {log_file}")
    print("\n✓ All tests passed!")

except ImportError as e:
    print(f"✗ ERROR: Failed to import modules: {e}")
    print("\nNote: This test requires the project dependencies to be installed.")
    print("Run: uv sync")
    sys.exit(1)
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
