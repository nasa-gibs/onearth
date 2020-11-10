#!/usr/bin/env python3

import os
import sys
import json
import glob

log_dir = sys.argv[1]
output = sys.argv[2]

print("Using input directory " + log_dir + " and output file " + output)

events = []
json_files = glob.glob(log_dir+"/*.json")

for json_file in json_files:
    print("Reading: " + json_file)
    with open(json_file) as json_data:
        json_d = json.load(json_data)
        for event in json_d["events"]:
            events.append(event)
            
print("Found " + str(len(events)) + " events")
json_out = {"events":events}
json_out_file = open(output, 'w')
json.dump(json_out, json_out_file, indent=4)