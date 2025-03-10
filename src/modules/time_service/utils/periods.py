#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script calculates periods and calls periods.lua to update redis
"""

import argparse
from datetime import datetime
import dateutil.relativedelta as rd
import redis
import sys
import re

DEBUG = False

# Format a list of periods for adding to redis using zadd.
# zadd requires a dictionary in the form of {item: score}
def get_zadd_dict(periods):
    return dict(zip(map(lambda x: x, periods), [0] * len(periods)))

# Returns a dateutil.relativedelta determined from a given period interval
def get_rd_from_interval(period_interval):
    match = re.search(r'(-|P|PT)(\d+)(\D+)', period_interval)
    prefix = match.group(1)
    count = int(match.group(2))
    interval = match.group(3)
    rel_delta = None
    if interval == 'Y':
        rel_delta = rd.relativedelta(years=count)
    elif interval == 'M' and prefix != 'PT':
        rel_delta = rd.relativedelta(months=count)
    elif interval == 'D':
        rel_delta = rd.relativedelta(days=count)
    elif interval == 'H':
        rel_delta = rd.relativedelta(hours=count)
    elif interval == 'MM':
        rel_delta = rd.relativedelta(minutes=count)
    elif interval == 'S':
        rel_delta = rd.relativedelta(seconds=count)
    else:
        print(f'Error: invalid interval encountered in {period_interval}, must be Y, M, D, H, MM, or S')
        sys.exit(1)
    return rel_delta

# Returns an ISO 8601 duration from a dateutil.relativedelta
def get_duration_from_rd(rel_delta):
    duration = 'P'
    if rel_delta.years != 0:
        duration += str(rel_delta.years) + 'Y'
    if rel_delta.months != 0:
        duration += str(rel_delta.months) + 'M'
    if rel_delta.days != 0:
        duration += str(rel_delta.days) + 'D'
    if rel_delta.hours != 0:
        if 'T' not in duration:
            duration += 'T'
        duration += str(rel_delta.hours) + 'H'
    if rel_delta.minutes != 0:
        if 'T' not in duration:
            duration += 'T'
        duration += str(rel_delta.minutes) + 'MM'
    if rel_delta.seconds != 0:
        if 'T' not in duration:
            duration += 'T'
        duration += str(rel_delta.seconds) + 'S'
    return duration

def find_periods_and_breaks(dates, interval):
    new_periods = []
    duration = get_duration_from_rd(interval)
    size = re.search(r'(\d+)', duration).group(1)
    unit = re.search(r'\d+(\D+)', duration).group(1)
    start_date = dates[0]
    prev_date = start_date
    for date in dates[1:]:
        if datetime.fromisoformat(prev_date) + interval != datetime.fromisoformat(date):
            new_periods.append({'start': start_date,
                                'end': prev_date,
                                'size': size,
                                'unit': unit})
            start_date = date
        prev_date = date
    new_periods.append({'start': start_date,
                        'end': prev_date,
                        'size': size,
                        'unit': unit})
    return new_periods

# Returns the period strings for a given time config
def calculate_periods_from_config(dates, config, start_date, end_date, find_smallest_interval = False):
    # Parse time configurations
    config_parts = config.split('/')
    force_start = 'DETECT'
    force_end = 'DETECT'
    force_period = 'DETECT'
    if len(config_parts) == 3:
        force_end = config_parts[1]
        force_period = config_parts[2]
    elif len(config_parts) == 2:
        if 'P' in config_parts[1]:
            force_period = config_parts[1]
        else:
            force_end = config_parts[1]
    # If we're using minutes, make sure we have MM instead of M to avoid confusion with months
    if 'PT' in force_period and force_period.endswith('M') and 'MM' not in force_period:
        force_period = force_period + 'M'
    if 'false' not in config_parts[0]:
        force_start = config_parts[0]
    
    if DEBUG:
        print("config:", config)
        print("force_start=" + force_start)
        print("force_end=" + force_end)
        print("force_period=" + force_period)

    # Don't return any periods if using DETECT or LATEST and no dates are available
    if len(dates) == 0:
        if force_start == 'DETECT' or force_end == 'DETECT':
            print("No dates available for DETECT")
            return []
        if force_start.startswith('LATEST') or force_end == 'LATEST':
            print("No dates available for LATEST")
            return []
    
    # Translate LATEST into actual dates
    if force_start.startswith('LATEST'):
        rel_delta = get_rd_from_interval(force_start)
        force_start = (datetime.fromisoformat(dates[-1]) - rel_delta).isoformat()

    if force_end == 'LATEST':
        force_end = dates[-1]

    # If not using DETECT and we have start_date and/or end_date,
    # trim the time config's force_start and/or force_end to match start_date and/or end_date
    if start_date:
        if force_end != 'DETECT' and datetime.fromisoformat(force_end) < datetime.fromisoformat(start_date):
            return []
        elif force_start != 'DETECT' and datetime.fromisoformat(start_date) > datetime.fromisoformat(force_start):
            force_start = start_date
    if end_date:
        if force_start != 'DETECT' and datetime.fromisoformat(force_start) > datetime.fromisoformat(end_date):
            return []
        elif force_end != 'DETECT' and datetime.fromisoformat(end_date) < datetime.fromisoformat(force_end):
            force_end = end_date

    # Detect periods
    periods = []

    # Skip DETECT if all values are forced
    if force_start != 'DETECT' and force_end != 'DETECT' and force_period != 'DETECT':
        size = re.search(r'(\d+)', force_period).group(1)
        unit = re.search(r'\d+(\D+)', force_period).group(1)
        periods.append({'start': force_start,
                        'end': force_end,
                        'size': size,
                        'unit': unit})
    # Detect periods
    else:
        # Filter out any dates that occur before force_start or after force_end,
        # or fall outside of start_date and end_date
        start_idx = 0
        end_idx = len(dates) - 1
        if force_start != 'DETECT' or start_date:
            if force_start == 'DETECT':
                start_datetime = datetime.fromisoformat(start_date)
            else:
                start_datetime = datetime.fromisoformat(force_start)
            while start_datetime > datetime.fromisoformat(dates[start_idx]):
                start_idx = start_idx + 1
                if start_idx >= len(dates):
                    print(f'No dates available to detect for a forced start date of {start_datetime.isoformat()}')
                    return []
        if force_end != 'DETECT' or end_date:
            if force_end == 'DETECT':
                end_datetime = datetime.fromisoformat(end_date)
            else:
                end_datetime = datetime.fromisoformat(force_end)
            while end_datetime < datetime.fromisoformat(dates[end_idx]):
                end_idx = end_idx - 1
                if end_idx < 0:
                    print(f'No dates available to detect for a forced end date of {end_datetime.isoformat()}')
                    return []
    
        trimmed_dates = dates[start_idx:end_idx + 1]
        
        # Calculate periods based on dates list
        
        if len(trimmed_dates) > 1:
            # Use the given size and interval of the period if they are present.
            if force_period != 'DETECT':
                interval = get_rd_from_interval(force_period)
            else:
                # Use the interval between the first and second dates if that equals the interval between the second and third dates
                # This is how periods.lua would determine the interval.
                # Faster for layers with many dates, but may not be the best choice if the beginning intervals are different from the rest.
                first_relative_interval = rd.relativedelta(datetime.fromisoformat(trimmed_dates[1]), datetime.fromisoformat(trimmed_dates[0]))
                if not find_smallest_interval and len(trimmed_dates) > 2 and first_relative_interval == rd.relativedelta(datetime.fromisoformat(trimmed_dates[2]), datetime.fromisoformat(trimmed_dates[1])):
                    interval = first_relative_interval
                    
                # Otherwise figure out the size and interval of the period based on the smallest interval between two dates
                else:
                    min_interval = datetime.fromisoformat(trimmed_dates[1]) - datetime.fromisoformat(trimmed_dates[0])
                    min_interval_start_date = trimmed_dates[0]
                    min_interval_end_date = trimmed_dates[1]
                    for i in range(len(trimmed_dates) - 1):
                        current_interval  = datetime.fromisoformat(trimmed_dates[i + 1]) - datetime.fromisoformat(trimmed_dates[i])
                        if current_interval < min_interval:
                            min_interval = current_interval
                            min_interval_start_date = trimmed_dates[i]
                            min_interval_end_date = trimmed_dates[i + 1]
                
                    interval = rd.relativedelta(datetime.fromisoformat(min_interval_end_date), datetime.fromisoformat(min_interval_start_date))
            new_periods = find_periods_and_breaks(trimmed_dates, interval)
            periods.extend(new_periods)
        
        # Single date in this period
        elif len(trimmed_dates) == 1 and trimmed_dates[0]:
            # Default to P1D
            if force_period == 'DETECT':
                size = 1
                unit = 'D'
            else:
                size = re.search(r'(\d+)', force_period).group(1)
                unit = re.search(r'\d+(\D+)', force_period).group(1)
            periods.append({'start': trimmed_dates[0],
                            'end': trimmed_dates[0],
                            'size': size,
                            'unit': unit})
        
        # Replace the first date of the first period and/or last date of
        # the last period with forced values as appropriate
        if len(periods) > 0:
            if force_start != 'DETECT':
                if force_period.startswith('PT') and len(force_start) < 11:
                    force_start = force_start + 'T00:00:00'
                periods[0]['start'] = force_start
            
            if force_end != 'DETECT':
                if force_period.startswith('PT') and len(force_end) < 11:
                    force_end = force_end + 'T00:00:00'
                periods[-1]['end'] = force_end

    # Create formatted list
    period_strings = []
    for period_dict in periods:
        period_str = ''
        if force_period != 'DETECT':
            size = re.search(r'(\d+)', force_period).group(1)
            unit = re.search(r'\d+(\D+)', force_period).group(1)
            period_dict['size'] = size
            period_dict['unit'] = unit
        period_str = f'{period_dict["start"]}Z/{period_dict["end"]}Z/PT{period_dict["size"]}{period_dict["unit"]}'
        # Subdaily intervals
        if period_dict['unit'] in ['H', 'MM', 'S']:
            # represent minutes with a single 'M'
            period_str = period_str.replace('MM', 'M')
        # Whole date intervals
        else:
            period_str = period_str.replace('T00:00:00', '')
            # 'PT' is only used when the interval is subdaily
            period_str = period_str.replace('PT', 'P')
            # Remove 'Z' if we don't have times associated with the dates
            if 'T' not in period_str:
                period_str = period_str.replace('Z', '')
        period_strings.append(period_str)

        if DEBUG:
            print("Added period", period_str, "for config", config)

    return period_strings                
    

def calculate_layer_periods(redis_port, redis_uri, layer_key, new_datetime=None, expiration=False, start_date=None, end_date=None, keep_existing_periods=False, find_smallest_interval=False, debug=False):
    print(f'Calculating time periods for {layer_key}')
    DEBUG = debug
    r = redis.Redis(host=redis_uri, port=redis_port)

    # Keep track of the layers that we should update
    layer_keys = [layer_key]

    # We will also be applying any changes we make to a layer specified by :copy_layer
    copy_layer = r.get(f'{layer_key}:copy_dates')
    if copy_layer:
        # Use the same prefix as the main layer
        prefix_match = re.match(r'(.*):', layer_key)
        if prefix_match:
            copy_key = f"{prefix_match.group(1)}:{copy_layer.decode('utf-8')}"
        else:
            copy_key = copy_layer.decode('utf-8')
        layer_keys.append(copy_key)

    # Add the new date to the list of dates for each key (if applicable)
    if new_datetime:
        for key in layer_keys:
            result = r.zadd(f'{key}:dates', {new_datetime: 0})
            # Add the date to the expiration key (if applicable)
            if expiration:
                result = r.zadd(f'{key}:expiration', {new_datetime: 0})
            if result == 0:
                if DEBUG:
                    print(f'{key}:dates already has {new_datetime}, no changes will be made')
                return
    
    # Get all dates for the layer
    dates_bytes = r.zrange(f'{layer_key}:dates', 0, -1)
    # convert to strings
    dates = [date_byte.decode('utf-8') for date_byte in dates_bytes]

    # Get all time configurations for the layer
    configs_bytes = sorted(r.smembers(f'{layer_key}:config'))
    configs = [config_byte.decode('utf-8') for config_byte in configs_bytes]

    # Default to DETECT if no time configurations are found
    if len(configs) == 0:
        configs = ['DETECT']

    # Calculate the periods for each time config
    calculated_periods = []
    for config in configs:
        new_periods = calculate_periods_from_config(dates, config, start_date, end_date, find_smallest_interval)
        calculated_periods = calculated_periods + new_periods

    for key in layer_keys:
        is_set = r.type(f'{key}:periods') == b'set'
        
        # Situations where we'll need to add all calculated periods to the periods key
        if keep_existing_periods or is_set:
            if r.exists(f'{key}:periods') == 1 and not keep_existing_periods:
                r.delete(f'{key}:periods')
            
            if len(calculated_periods) > 0:
                # Add everything as an unsorted set only when the periods key is already
                # an unsorted set and we're keeping all the existing periods
                if keep_existing_periods and is_set:
                    r.sadd(f'{key}:periods', *calculated_periods)
                else:
                    r.zadd(f'{key}:periods', get_zadd_dict(calculated_periods))

        # Otherwise, only do the minimum modifications necessary to Redis
        else:
            existing_periods_bytes = r.zrange(f'{key}:periods', 0, -1)
            existing_periods = [period_bytes.decode('utf-8') for period_bytes in existing_periods_bytes]
            
            # Determine which calculated periods aren't already in redis
            periods_to_add = []
            for new_period in calculated_periods:
                if new_period not in existing_periods:
                    periods_to_add.append(new_period)

            # Determine which periods in redis did not reappear after recalculation
            periods_to_remove = []
            for old_period in existing_periods:
                if old_period not in calculated_periods:
                    periods_to_remove.append(old_period)

            # Update redis
            if len(periods_to_add) > 0:
                r.zadd(f'{key}:periods', get_zadd_dict(periods_to_add))
            if len(periods_to_remove) > 0:
                r.zrem(f'{key}:periods', *periods_to_remove)

    
    # Update :default key
    default_date = None
    # Use most recent date of the most recent period
    if len(calculated_periods) > 0:
        default_date = sorted(calculated_periods)[-1].split('/')[1]

    # If there are no periods, then use the last config time
    else:
        # Find the last time config that doesn't have 'DETECT'
        last_config = None
        for config in reversed(configs):
            if 'DETECT' not in config:
                last_config = config
                break
        if last_config:
            last_config_parts = last_config.split('/')
            for part in reversed(last_config_parts):
                if re.search(r'\d{4}-\d{2}-\d{2}', part):
                    default_date = part
    if default_date:
        if len(calculated_periods) > 0 and 'PT' not in calculated_periods[-1]:
            default_date = re.sub(r'T00:00:00Z?', '', default_date)
        for key in layer_keys:
            r.set(f'{key}:default', default_date)
    else:
        print('Warning: no default date could be determined.')
    
    print('Periods added to', layer_key)


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Loads custom period configurations')
    parser.add_argument('layer_key',
                        help='layer_prefix:layer_name that periods should be calculated for')
    parser.add_argument('-d', '--datetime',
                        dest='new_datetime',
                        metavar='NEW_DATETIME',
                        type=str,
                        help='New datetime that is to be added to the periods for this layer')
    parser.add_argument('-x', '--expiration',
                        dest='expiration',
                        metavar='EXPIRATION',
                        type=bool,
                        default=False,
                        help='Add the new date to the layer_key:expiration redis key')
    parser.add_argument('-s', '--start_date',
                        dest='start_date',
                        metavar='START_DATE',
                        type=str,
                        help='Only dates that take place after this value will be considered while calculating periods')
    parser.add_argument('-e', '--end_date',
                        dest='end_date',
                        metavar='END_DATE',
                        type=str,
                        help='Only dates that take place before this value will be considered while calculating periods')
    parser.add_argument('-k', '--keep_existing_periods',
                        dest='keep_existing_periods',
                        action='store_true',
                        default=False,
                        help='Don\'t delete existing periods at :periods before adding the newly calculated periods. Note that this can lead to overlapping periods. Most useful when using --start_datetime and --end_datetime.')
    parser.add_argument('-f', '--find_smallest_interval',
                        dest='find_smallest_interval',
                        action='store_true',
                        default=False,
                        help='Force the script to calculate the interval for each period based on the smallest interval between any two dates. For performance reasons, the script would otherwise only do this if the intervals between the first and second dates and second and third dates differ.')
    parser.add_argument('-p', '--port',
                        dest='port',
                        action='store',
                        default=6379,
                        help='redis port for database')
    parser.add_argument('-r', '--redis_uri',
                        dest='redis_uri',
                        metavar='REDIS_URI',
                        type=str,
                        help='URI for the Redis database')
    parser.add_argument('-v', '--verbose',
                        dest='debug',
                        action='store_true',
                        default=False,
                        help='Print additional log messages')
    args = parser.parse_args()

    calculate_layer_periods(args.port,
                            args.redis_uri,
                            args.layer_key,
                            args.new_datetime,
                            args.expiration,
                            args.start_date,
                            args.end_date,
                            args.keep_existing_periods,
                            args.find_smallest_interval,
                            args.debug
                        )
