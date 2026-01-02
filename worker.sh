#!/bin/bash
source venv/bin/activate && celery -A theoneeye worker -l info