#!/bin/bash
source venv/bin/activate && daphne -b 0.0.0.0 -p 7878 theoneeye.asgi:application