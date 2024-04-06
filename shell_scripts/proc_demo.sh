#!/bin/bash

counter=0
while true; do 

    for ((i=0; i<1000000;i++)) do
        result=$(echo "scale=10; $i * $i" | bc)
    done
    echo "$counter" >> /home/soar/Scripts/runlog.log
    ((counter += 1))
    sleep 1
done