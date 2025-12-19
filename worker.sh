#!/bin/bash
source /home/roshan/anaconda3/etc/profile.d/conda.sh
conda activate theoneeye && celery -A theoneeye worker -l info