#!/usr/bin/env python3

import requests
import telnetlib
import time
import sys


def test_http_traffic():
    """Generate HTTP traffic with credentials"""
    try:
        print("Generating HTTP traffic...")
        # Test with HTTP server
        url = "http://10.0.0.2"
        data = {"user": "testuser", "pass": "testpass123"}

        response = requests.post(url, data=data, timeout=5)
        print(f"HTTP request sent to {url}")

    except Exception as e:
        print(f"HTTP test failed: {e}")


def test_telnet_traffic():
    """Generate Telnet traffic with credentials"""
    try:
        print("Generating Telnet traffic...")
        # Connect to telnet server
        tn = telnetlib.Telnet("10.0.0.3", 23, timeout=10)

        # Wait for login prompt
        tn.read_until(b"login:", timeout=5)
        tn.write(b"afzal\n")

        # Wait for password prompt
        tn.read_until(b"Password:", timeout=5)
        tn.write(b"2005021\n")

        # Read response
        response = tn.read_some()
        print(f"Telnet response: {response}")

        tn.close()
        print("Telnet connection completed")

    except Exception as e:
        print(f"Telnet test failed: {e}")


def main():
    print("Starting traffic generation...")

    # Wait a bit for services to be ready
    time.sleep(2)

    # Generate different types of traffic
    test_http_traffic()
    time.sleep(1)
    test_telnet_traffic()

    print("Traffic generation completed")


if __name__ == "__main__":
    main()
