#!/bin/bash
source /home/roshan/anaconda3/etc/profile.d/conda.sh
conda activate theoneeye && daphne -p 7878 theoneeye.asgi:application