#!/bin/sh

base_dir=$(dirname $(readlink -f $0))
#/home/omer/git/detect_dog

if ! tmux has-session -t dog_detect; then
    tmux new-session -d -s dog_detect -n dog_detect
    tmux split-window -v -t dog_detect
fi

tmux send-keys -t dog_detect.1 "cd $base_dir" C-m
tmux send-keys -t dog_detect.1 "pipenv run ./app.py --src v4l2 --dst output --params params.json --log no-dog-zone.log -v" C-m
