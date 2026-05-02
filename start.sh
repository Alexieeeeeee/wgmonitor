#!/bin/bash

# 启动WireGuard监控应用
source .venv/bin/activate
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000