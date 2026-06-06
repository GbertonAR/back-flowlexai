#!/bin/bash
# Azure App Service startup script — FlowLexAI Backend
mkdir -p /home/data/vectors
cd /home/site/wwwroot
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
