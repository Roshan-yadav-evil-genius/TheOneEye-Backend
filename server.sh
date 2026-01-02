#!/bin/bash
source venv/bin/activate && daphne -p 7878 theoneeye.asgi:application