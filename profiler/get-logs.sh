#!/bin/bash

list_urls=test-time-jpeg
output_prefix=log-time-jpeg-N
group_name=''

mkdir $output_prefix
i="0"
reps="10"
while [ $i -lt $reps ]
do
output_prefix_i=$output_prefix$i
echo $output_prefix_i
start_time=$(( ( $(date -u +"%s") - 1 ) * 1000 ))
echo "start" $start_time
siege -f $list_urls -r 100 -c 100 > $output_prefix_i.siege.txt
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
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "begin_mod_reproject_handle" --start-time $start_time > $output_prefix/$output_prefix_i-begin_mod_mrf.json
aws logs filter-log-events --log-group-name "$group_name" --filter-pattern "end_mod_reproject_handle" --start-time $start_time > $output_prefix/$output_prefix_i-end_mod_mrf.json
i=$[$i+1]
sleep 10
done