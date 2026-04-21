#!/bin/bash
# ============================================================
# ITCS-6190 Assignment 3 — EC2 Setup Script
# Run this after SSHing into your Amazon Linux 2023 instance
# ============================================================

set -e  # Exit immediately on any error

echo "==> Updating system packages..."
sudo yum update -y

echo "==> Installing Python 3 pip..."
sudo yum install python3-pip -y

echo "==> Installing Flask and Boto3..."
pip3 install Flask boto3

echo "==> All dependencies installed."
echo ""
echo "Next steps:"
echo "  1. Create app.py:  nano app.py"
echo "  2. Paste the contents of EC2InstanceNANOapp..py"
echo "  3. Update AWS_REGION, ATHENA_DATABASE, and S3_OUTPUT_LOCATION"
echo "  4. Save and exit nano (Ctrl+X, Y, Enter)"
echo "  5. Run the app: python3 app.py"
echo "  6. Open browser: http://<YOUR-EC2-PUBLIC-IP>:5000"
