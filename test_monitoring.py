#!/usr/bin/env python3
"""
Test script to verify Sentry and Socket monitoring integration.
Run this script to test that both services are properly configured.
"""

import os
import sys
import subprocess

def test_sentry():
    """Test Sentry error tracking integration."""
    print("🧪 Testing Sentry integration...")

    try:
        import sentry_sdk
        from sentry_sdk import capture_exception

        dsn = os.getenv("SENTRY_DSN")
        if not dsn:
            print("❌ SENTRY_DSN not set. Please set your Sentry DSN.")
            return False

        # Initialize Sentry (this should already be done by main.py)
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
            traces_sample_rate=1.0,
        )

        # Send a test error
        capture_exception(Exception("Test error from LazyScan monitoring test"))
        print("✅ Test error sent to Sentry successfully!")
        return True

    except ImportError:
        print("❌ sentry-sdk not installed. Run: pip install sentry-sdk")
        return False
    except Exception as e:
        print(f"❌ Sentry test failed: {e}")
        return False

def test_socket():
    """Test Socket CLI integration."""
    print("🧪 Testing Socket CLI integration...")

    try:
        # Check if socket CLI is available
        result = subprocess.run(["/Users/vinayvidyasagar/.nvm/versions/node/v23.11.0/bin/socket", "--version"],
                              capture_output=True, text=True, timeout=10)

        # Check if we got version info (CLI: v...) - socket returns exit code 2 for --version
        if "CLI: v" in result.stdout or "CLI: v" in result.stderr:
            print("✅ Socket CLI is installed and working!")
            # Check authentication by looking for token and org in output
            output = result.stdout + result.stderr
            if "token:" in output and "org:" in output:
                print("✅ Socket CLI is authenticated!")
                return True
            else:
                print("❌ Socket CLI not authenticated. Run: socket login")
                return False
        else:
            print("❌ Socket CLI not found. Install with: npm install -g @socketsecurity/cli")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Socket CLI test timed out")
        return False
    except FileNotFoundError:
        print("❌ Socket CLI not installed")
        return False
    except Exception as e:
        print(f"❌ Socket test failed: {e}")
        return False

def main():
    """Run all monitoring tests."""
    print("🚀 LazyScan Monitoring Integration Test")
    print("=" * 50)

    sentry_ok = test_sentry()
    print()
    socket_ok = test_socket()

    print("\n" + "=" * 50)
    print("📊 Test Results:")

    if sentry_ok:
        print("✅ Sentry: Configured and working")
    else:
        print("❌ Sentry: Not configured or failing")

    if socket_ok:
        print("✅ Socket: CLI installed and authenticated")
    else:
        print("❌ Socket: CLI not installed or not authenticated")

    if sentry_ok and socket_ok:
        print("\n🎉 All monitoring integrations are working!")
        print("\nNext steps:")
        print("1. Set up GitHub integration for Socket: https://socket.dev")
        print("2. Create Sentry project and get DSN: https://sentry.io")
        print("3. Add environment variables to .env file")
        print("4. Push code to trigger CI/CD monitoring")
    else:
        print("\n⚠️  Some integrations need setup. See instructions above.")

    return 0 if (sentry_ok and socket_ok) else 1

if __name__ == "__main__":
    sys.exit(main())