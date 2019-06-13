#!/bin/bash

list_urls=${1:-urls}
group_name=${2:-onearth}
output_prefix=${3:test2}
reps=${4:-10}
requests=${5:-100}
users=${6:-100}

mkdir $output_prefix
i="0"
while [ $i -lt $reps ]
do
output_prefix_i=$output_prefix$i
echo $output_prefix_i
start_time=$(( ( $(date -u +"%s") - 1 ) * 1000 ))
echo "start" $start_time
siege -f $list_urls -r $requests -c $users > $output_prefix_i.siege.txt
sleep 80
end_time=$(( ( $(date -u +"%s") ) * 1000 ))
echo "end" $end_time
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "begin_onearth_handle" --start-time $start_time > $output_prefix/$output_prefix_i-begin_onearth.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "end_onearth_handle" --start-time $start_time > $output_prefix/$output_prefix_i-end_onearth.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "begin_mod_mrf_handle" --start-time $start_time > $output_prefix/$output_prefix_i-begin_mod_mrf.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "end_mod_mrf_handle" --start-time $start_time > $output_prefix/$output_prefix_i-end_mod_mrf.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "begin_send_to_date_service" --start-time $start_time > $output_prefix/$output_prefix_i-begin_send_to_date_service.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "end_send_to_date_service" --start-time $start_time > $output_prefix/$output_prefix_i-end_send_to_date_service.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "mod_mrf_s3_read" --start-time $start_time > $output_prefix/$output_prefix_i-s3.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "mod_mrf_index_read" --start-time $start_time > $output_prefix/$output_prefix_i-idx.json
i=$[$i+1]
sleep 10
done

python ../cat_event_logs.py $output_prefix $output_prefix.json
