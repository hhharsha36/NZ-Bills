#!/usr/bin/env bash
# TODO: check if commented out line has any impact when ran using Docker
#flask db upgrade
flask run --host=0.0.0.0 --port 5001
