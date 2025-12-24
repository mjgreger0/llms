#!/usr/bin/env python3
"""Test script to validate configuration module."""

import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent))


def test_config_loading():
    """Test configuration loads with various environment variable scenarios."""
    print("Testing Configuration Module")
    print("=" * 60)

    # Test 1: Missing required DASHBOARD_URL
    print("\n1. Testing missing DASHBOARD_URL (should fail)...")
    os.environ.pop("DASHBOARD_URL", None)
    try:
        from src.config import Config
        config = Config()
        print("   ❌ FAILED: Should have raised validation error")
        return False
    except Exception as e:
        print(f"   ✓ PASS: Correctly raised error: {type(e).__name__}")

    # Test 2: Valid configuration with defaults
    print("\n2. Testing valid config with defaults...")
    os.environ["DASHBOARD_URL"] = "ws://localhost:8080/ws/daemon"
    try:
        from src.config import Config
        config = Config()
        print(f"   ✓ PASS: Config loaded successfully")
        print(f"   - DASHBOARD_URL: {config.DASHBOARD_URL}")
        print(f"   - MACHINE_ID: {config.MACHINE_ID} (auto-generated)")
        print(f"   - PROC_PATH: {config.PROC_PATH}")
        print(f"   - SYS_PATH: {config.SYS_PATH}")
        print(f"   - PODMAN_SOCKET: {config.PODMAN_SOCKET}")
        print(f"   - MODEL_PATH: {config.MODEL_PATH}")
        print(f"   - STATS_INTERVAL_SECONDS: {config.STATS_INTERVAL_SECONDS}")
        print(f"   - HEALTH_CHECK_INTERVAL_SECONDS: {config.HEALTH_CHECK_INTERVAL_SECONDS}")
        print(f"   - LOG_LEVEL: {config.LOG_LEVEL}")
        print(f"   - LOG_FORMAT: {config.LOG_FORMAT}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    # Test 3: Custom MACHINE_ID
    print("\n3. Testing custom MACHINE_ID...")
    os.environ["MACHINE_ID"] = "gpu-node-001"
    try:
        # Need to reimport to pick up new env var
        import importlib
        import src.config
        importlib.reload(src.config)
        config = src.config.Config()
        if config.MACHINE_ID == "gpu-node-001":
            print(f"   ✓ PASS: MACHINE_ID set to: {config.MACHINE_ID}")
        else:
            print(f"   ❌ FAILED: MACHINE_ID is {config.MACHINE_ID}, expected gpu-node-001")
            return False
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    # Test 4: Invalid interval (negative)
    print("\n4. Testing invalid interval (negative, should fail)...")
    os.environ["STATS_INTERVAL_SECONDS"] = "-1"
    try:
        import importlib
        import src.config
        importlib.reload(src.config)
        config = src.config.Config()
        print("   ❌ FAILED: Should have rejected negative interval")
        return False
    except Exception as e:
        print(f"   ✓ PASS: Correctly rejected negative interval: {type(e).__name__}")

    # Test 5: Valid custom intervals
    print("\n5. Testing custom intervals...")
    os.environ["STATS_INTERVAL_SECONDS"] = "10"
    os.environ["HEALTH_CHECK_INTERVAL_SECONDS"] = "3"
    try:
        import importlib
        import src.config
        importlib.reload(src.config)
        config = src.config.Config()
        if config.STATS_INTERVAL_SECONDS == 10 and config.HEALTH_CHECK_INTERVAL_SECONDS == 3:
            print(f"   ✓ PASS: Intervals set correctly")
            print(f"   - STATS_INTERVAL_SECONDS: {config.STATS_INTERVAL_SECONDS}")
            print(f"   - HEALTH_CHECK_INTERVAL_SECONDS: {config.HEALTH_CHECK_INTERVAL_SECONDS}")
        else:
            print(f"   ❌ FAILED: Intervals not set correctly")
            return False
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All configuration tests passed!")
    return True


def test_logging():
    """Test logging configuration."""
    print("\n\nTesting Logging Module")
    print("=" * 60)

    # Set up environment for logging test
    os.environ["DASHBOARD_URL"] = "ws://localhost:8080/ws/daemon"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["LOG_FORMAT"] = "json"

    try:
        # Reimport to pick up new config
        import importlib
        import src.config
        import src.logger
        importlib.reload(src.config)
        importlib.reload(src.logger)

        from src.logger import logger

        print("\n1. Testing JSON format logging...")
        logger.info("test_message", test_field="test_value", number=42)
        print("   ✓ PASS: JSON log output above")

        # Test console format
        print("\n2. Testing console format logging...")
        os.environ["LOG_FORMAT"] = "console"
        importlib.reload(src.config)
        importlib.reload(src.logger)
        from src.logger import logger as console_logger
        console_logger.info("console_test_message", test_field="test_value")
        print("   ✓ PASS: Console log output above")

        # Test different log levels
        print("\n3. Testing different log levels...")
        console_logger.debug("debug message")
        console_logger.info("info message")
        console_logger.warning("warning message")
        console_logger.error("error message")
        print("   ✓ PASS: All log levels work")

        print("\n" + "=" * 60)
        print("✓ All logging tests passed!")
        return True

    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_loading()
    if success:
        success = test_logging()

    sys.exit(0 if success else 1)
