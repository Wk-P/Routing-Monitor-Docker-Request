#!/bin/bash

process_name=$1
log_path="/home/soar/Scripts/monitorlog.log"
pid=$(pgrep "$process_name")

echo "" > $log_path

# first time /proc/pid/stat
prev_proc_time=$(awk '{ print $14 + $15 + $16 + $17 }' /proc/$pid/stat)

# inteval time (ms)
interval=1000

interrupt_time=0.5

sleep $interrupt_time

while true; do
    if [ -n "$pid" ]; then
        curr_proc_time=$(awk '{ print $14 + $15 + $16 + $17 }' /proc/$pid/stat)


        cpu_usage_percentage=$(echo "scale=2; $((curr_proc_time - prev_proc_time)) / $interval / $interrupt_time * 100" | bc)
        mem_usage=$(awk '{ print $2 }' /proc/$pid/statm)
        page_size=$(getconf PAGESIZE)
        
        prev_proc_time=$curr_proc_time
        echo "CPU:$cpu_usage_percentage%"
        echo "PROC $pid 's cpu usage => $cpu_usage_percentage%" >> $log_path
        echo "PROC $pid 's mem usage => $((mem_usage * page_size)) bytes" >> $log_path
        echo "" >> $log_path
        # printf "CPU USAGE => %.2f%%\n" "$cpu_usage_percentage"
    else
        echo "No proc with PID is $pid" | tee $log_path
        # break
    fi
    sleep $interrupt_time
done