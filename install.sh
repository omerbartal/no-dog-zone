#!/bin/bash

echo "installing dependecies..."
pipenv install
mkdir output

echo
echo "downloading model..."
mkdir yolo4tiny/
wget https://github.com/omerbartal/yolov4-opencv-python/raw/master/yolov4-tiny.weights -O yolo4tiny/yolov4-tiny.weights -o /dev/null
wget https://github.com/omerbartal/yolov4-opencv-python/raw/master/yolov4-tiny.cfg -O yolo4tiny/yolov4-tiny.cfg -o /dev/null
wget https://github.com/omerbartal/yolov4-opencv-python/raw/master/classes.txt -O yolo4tiny/classes.txt -o /dev/null

echo
echo "add the following line to /etc/rc.local:"
echo "sudo -u $USER $(readlink -f boot.sh)"
