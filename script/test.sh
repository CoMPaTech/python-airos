#!/usr/bin/env sh
pytest tests --cov=airos --cov-report term-missing "${1}"
