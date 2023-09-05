#!/usr/bin/env bash
# TODO: check if commented out line has any impact when ran using Docker
#flask db upgrade
python3 -m pip install -r requirements.txt
python3 scripts/dyndb_create_pm_table.py
python3 scripts/dyndb_create_users_table.py
flask run --host=0.0.0.0 --port 5001
