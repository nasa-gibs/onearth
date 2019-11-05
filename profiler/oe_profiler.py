#!/usr/bin/env python3.6

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import argparse
import yaml
import collections
import math
import random
import subprocess
from datetime import timedelta
from datetime import datetime

version = '2.2.3'

tilematrixsets_geo = {
    '64km': [1,2], 
    '32km': [2,3],
    '16km': [3,5],
    '8km': [5,10],
    '4km': [10,20],
    '2km': [20,40],
    '1km': [40,80],
    '500m': [80,160],
    '250m': [160,320]}

tilematrixsets_wm = {
    'GoogleMapsCompatible_Level0': [1,1], 
    'GoogleMapsCompatible_Level1': [2,2],
    'GoogleMapsCompatible_Level2': [4,4],
    'GoogleMapsCompatible_Level3': [8,8],
    'GoogleMapsCompatible_Level4': [16,16],
    'GoogleMapsCompatible_Level5': [32,32],
    'GoogleMapsCompatible_Level6': [64,64], 
    'GoogleMapsCompatible_Level7': [128,128],
    'GoogleMapsCompatible_Level8': [256,256],
    'GoogleMapsCompatible_Level9': [512,512],
    'GoogleMapsCompatible_Level10': [1024,1024],
    'GoogleMapsCompatible_Level11': [2048,2048],
    'GoogleMapsCompatible_Level12': [4096,4096],
    'GoogleMapsCompatible_Level13': [8192,8192]}

style = 'default'

def random_time(start_time, end_time, interval):
    delta = end_time - start_time
    random_day = random.randrange(delta.days+1)
    rdate = start_time + timedelta(days=random_day)
    return datetime.strftime(rdate,'%Y-%m-%dT%H:%M:%SZ')

def run_test(test_dir, server, group_name, 
             number_requests, number_users, number_urls):
    
    print('Test directory: ' + test_dir)
    print('Server: ' + server)
    print('Log group: ' + group_name)
    with open(test_dir+'/test.yaml', 'r') as f:
        config = yaml.safe_load(f.read())

    base_url = config['base_url'].replace('$ONEARTH_HOST', server)
    print('Description: ' + config['description'])
    print('Base URL: ' + base_url)
    print('Period: ' + config['period'])
    print('Tilematrixset: ' + config['tilematrixset'])
    
    if 'GoogleMaps' in config['tilematrixset']: # Use Web Mercator tilematrixsets
        tilematrixsets = tilematrixsets_wm
    else:
        tilematrixsets = tilematrixsets_geo
    
    urls_file = 'urls'
    if os.path.isfile(test_dir + '/list_urls'):
        urls_file = 'list_urls'
    
    if config['period'] != '':
        start_time, end_time, interval = config['period'].split('/')
        if interval != 'P1D':
            print('Only 1 day periods are currently supported.')
        interval = 1
        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
        end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
        use_date = True
    else:
        use_date = False
        date_str = ''
    
    # generate URLs
    if urls_file != 'list_urls':
        urls = []
        zoom_max = 0
        tilematrixsets_list = list(tilematrixsets.items())
        for key, value in tilematrixsets_list:
            if key == config['tilematrixset']:
                break
            zoom_max += 1
        
        for i in range(number_urls):
            zoomlevel = random.randint(0,zoom_max)
            tiles = tuple(tilematrixsets_list[zoomlevel])[1]
            row_max, col_max = tiles[0], tiles[1]
            row = random.randint(0,row_max-1)
            col = random.randint(0,col_max-1)
            if use_date is True:
                date_str = random_time(start_time, end_time, interval) + '/'
            url = base_url +'/' + style + '/' + date_str + config['tilematrixset'] + '/' + str(zoomlevel) + '/' + str(row) + '/' + str(col)
            urls.append(url)
            
        with open(test_dir+'/urls', 'w') as f:
            for url in urls:
                 f.write(url+'\n')
        
    # run the test script
    requests = math.floor(number_requests/number_users)
    if requests >= 100:
        reps = math.floor(requests/100)
        requests = 100
    else:
        reps = 1
    run_test_commands = ['bash', 'run_test.sh', urls_file, group_name, test_dir, str(reps), str(requests), str(number_users)]
    print('Running in ' + test_dir + ': ' + ' '.join([str(v) for v in run_test_commands]))
    with open(test_dir+'/siege_out.txt','w+') as fout:
        with open(test_dir+'/siege_err.txt','w+') as ferr:
            run_test = subprocess.run(run_test_commands, cwd=test_dir, stdout=fout,stderr=ferr)
            fout.seek(0)
            output = fout.read()
            ferr.seek(0) 
            errors = ferr.read()
    print(output)
    print(errors)


def analyze_results(test_dir):
    analyze_commands = ['python3.6', 'analyze_event_log.py', '-e', test_dir + '/' + test_dir + '.json']
    print('\nRunning: ' + ' '.join([str(v) for v in analyze_commands]))
    with open(test_dir+'/'+test_dir+'.results.txt','w+') as fout:
        analyze = subprocess.run(analyze_commands, stdout=fout,stderr=fout)
        fout.seek(0)
        output = fout.read()
    print(output)


parser = argparse.ArgumentParser(
    description='Runs an OnEarth profiling test.')
parser.add_argument(
    '-t',
    '--test_dir',
    dest='test_dir',
    help='Test directory with configurations',
    action='store')
parser.add_argument(
    '-s',
    '--server',
    dest='server',
    action='store',
    default='localhost:8080',
    help='OnEarth host server used for testing')
parser.add_argument(
    '-g',
    '--group_name',
    dest='group',
    action='store',
    help='The log group name')
parser.add_argument(
    '-r',
    '--number_requests',
    dest='number_requests',
    action='store',
    default=100000,
    help='Total number of requests')
parser.add_argument(
    '-c',
    '--number_users',
    dest='number_users',
    action='store',
    default=100,
    help='Total number of concurrent users (max 100)')
parser.add_argument(
    '-u',
    '--number_urls',
    dest='number_urls',
    action='store',
    default=100,
    help='Total number of random l/r/c URLs (ignored if list_urls file is found)')
parser.add_argument(
    '-a',
    '--analysis_only',
    dest='analysis_only',
    default=False,
    help='Just analyze results; do not send requests',
    action='store_true')

args = parser.parse_args()

if args.analysis_only == False:
    run_test(args.test_dir, args.server, args.group, int(args.number_requests), int(args.number_users), int(args.number_urls))
analyze_results(args.test_dir)