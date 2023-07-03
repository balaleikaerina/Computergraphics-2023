#!/bin/bash

models=("models/bunny.obj" "models/cow.obj" "models/elephant.obj" "models/squirrel.obj" "models/squirrel_ar.obj" "models/suzanne_tri.obj")

for model in "${models[@]}"
do
    echo "Running $model"
    python3 oglTemplate.py $model
done


```

