#!/usr/bin/env python3
"""
OnEarth Time Service Python Module

A Python port of the Lua time service that provides time dimension handling
for OnEarth tile services with Redis backend support.

Licensed under the Apache License, Version 2.0
"""

import hashlib
import json
import math
import re
import socket
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import parse_qs, unquote
import redis


class OnearthTimeService:
    """OnEarth Time Service for handling temporal data queries."""
    
    # Date format templates
    DATE_TEMPLATE = r'^\d{4}-\d{1,2}-\d{1,2}$'
    DATETIME_TEMPLATE = r'^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{1,2}:\d{1,2}Z$'
    DATETIME_FILENAME_FORMAT = '%Y%j%H%M%S'
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    DATE_FORMAT = '%Y-%m-%d'
    
    def __init__(self):
        self.close_func = None
    
    @staticmethod
    def split(sep: str, string: str) -> List[str]:
        """Split string by separator."""
        return [s for s in string.split(sep) if s]
    
    @staticmethod
    def get_query_param(param: str, query_string: str) -> Optional[str]:
        """Extract query parameter value."""
        if not query_string:
            return None
        
        query_parts = query_string.split("&")
        for part in query_parts:
            if "=" in part:
                key, value = part.split("=", 1)
                if key.lower() == param.lower():
                    return unquote(value)
        return None
    
    @staticmethod
    def get_query_keys(query_string: str) -> List[str]:
        """Extract key0-key5 query parameters."""
        results = []
        if not query_string:
            return results
            
        query_parts = query_string.split("&")
        for part in query_parts:
            if "=" in part:
                key, value = part.split("=", 1)
                if re.match(r'^key[0-5]$', key):
                    results.append(unquote(value))
        return results
    
    @staticmethod
    def send_response(code: int, msg_string: str) -> Tuple[str, Dict[str, str], int]:
        """Format response for mod_ahtse_lua compatibility."""
        return msg_string, {"Content-Type": "application/json"}, code

    @staticmethod
    def parse_iso8601_duration(duration_string: str) -> Optional[Dict[str, int]]:
        """
        Parse ISO8601 duration strings with multiple units (e.g., P1DT2S, PT59M41S).
        Returns a dict with fields: years, months, weeks, days, hours, minutes, seconds.
        """
        if not duration_string or not isinstance(duration_string, str):
            return None

        match = re.match(r'^P([^T]*)T?(.*)$', duration_string)
        if not match:
            return None

        date_part, time_part = match.groups()

        years = int(re.search(r'(\d+)Y', date_part).group(1)) if re.search(r'(\d+)Y', date_part) else 0
        months = int(re.search(r'(\d+)M', date_part).group(1)) if re.search(r'(\d+)M', date_part) else 0
        weeks = int(re.search(r'(\d+)W', date_part).group(1)) if re.search(r'(\d+)W', date_part) else 0
        days = int(re.search(r'(\d+)D', date_part).group(1)) if re.search(r'(\d+)D', date_part) else 0

        hours = int(re.search(r'(\d+)H', time_part).group(1)) if time_part and re.search(r'(\d+)H', time_part) else 0
        minutes = int(re.search(r'(\d+)M', time_part).group(1)) if time_part and re.search(r'(\d+)M', time_part) else 0
        seconds = int(re.search(r'(\d+)S', time_part).group(1)) if time_part and re.search(r'(\d+)S', time_part) else 0

        return {
            'years': years,
            'months': months,
            'weeks': weeks,
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds
        }

    @staticmethod
    def duration_is_fixed(duration: Dict[str, int]) -> bool:
        """Check if duration is fixed (no years or months)."""
        return duration and duration.get('years', 0) == 0 and duration.get('months', 0) == 0

    @staticmethod
    def duration_fixed_total_seconds(duration: Dict[str, int]) -> int:
        """Calculate total seconds for fixed durations."""
        total_days = duration.get('weeks', 0) * 7 + duration.get('days', 0)
        total_seconds = total_days * 24 * 60 * 60
        total_seconds += duration.get('hours', 0) * 60 * 60
        total_seconds += duration.get('minutes', 0) * 60
        total_seconds += duration.get('seconds', 0)
        return total_seconds

    @staticmethod
    def add_interval(date_obj: datetime, duration: Dict[str, int]) -> datetime:
        """Add time interval to date based on duration object."""
        if duration.get('years', 0) != 0:
            date_obj = date_obj.replace(year=date_obj.year + duration['years'])
        if duration.get('months', 0) != 0:
            # Handle month addition properly
            month = date_obj.month
            year = date_obj.year
            month += duration['months']
            while month > 12:
                month -= 12
                year += 1
            date_obj = date_obj.replace(year=year, month=month)

        total_seconds = OnearthTimeService.duration_fixed_total_seconds(duration)
        if total_seconds != 0:
            date_obj = date_obj + timedelta(seconds=total_seconds)

        return date_obj
    
    def find_snap_date_for_fixed_time_interval(
        self,
        start_date: datetime,
        req_date: datetime,
        end_date: datetime,
        duration: Dict[str, int],
        snap_to_previous: bool
    ) -> Optional[datetime]:
        """Find snap date for fixed time intervals (no years or months)."""
        interval_in_sec = self.duration_fixed_total_seconds(duration)

        date_diff = (req_date - start_date).total_seconds()

        if snap_to_previous:
            closest_interval_date = start_date + timedelta(
                seconds=math.floor(date_diff / interval_in_sec) * interval_in_sec
            )
        else:
            closest_interval_date = start_date + timedelta(
                seconds=math.ceil(date_diff / interval_in_sec) * interval_in_sec
            )

        return closest_interval_date if closest_interval_date <= end_date else None
    
    def find_snap_date_for_non_fixed_time_interval(
        self,
        start_date: datetime,
        req_date: datetime,
        end_date: datetime,
        duration: Dict[str, int],
        snap_to_previous: bool
    ) -> Optional[datetime]:
        """Find snap date for non-fixed time intervals (Y, M)."""
        previous_interval_date = start_date

        while True:
            check_date = self.add_interval(previous_interval_date, duration)

            if check_date > req_date:  # Found snap date
                if snap_to_previous:
                    return previous_interval_date
                elif check_date <= end_date:
                    return check_date
                break

            if check_date > end_date:  # Snap date isn't in this period
                break

            previous_interval_date = check_date

        return None
    
    def get_snap_date(
        self,
        start_date: datetime,
        req_date: datetime,
        end_date: datetime,
        duration: Dict[str, int],
        snap_to_previous: bool
    ) -> Optional[datetime]:
        """Get snap date based on interval type."""
        if self.duration_is_fixed(duration):
            return self.find_snap_date_for_fixed_time_interval(
                start_date, req_date, end_date, duration, snap_to_previous
            )
        else:
            return self.find_snap_date_for_non_fixed_time_interval(
                start_date, req_date, end_date, duration, snap_to_previous
            )
    
    def time_snap(self, req_date: datetime, periods: List[str], snap_to_previous: bool) -> Tuple[Optional[datetime], int]:
        """Binary search for snap date in periods."""
        snap_date = None
        snap_period_idx = 1
        left, right = 0, len(periods) - 1

        while left <= right:
            mid = left + (right - left) // 2
            parsed_period = periods[mid].split("/")
            period_date = datetime.fromisoformat(parsed_period[0].replace('Z', '+00:00')).replace(tzinfo=None)

            if req_date == period_date:
                snap_date = req_date
                snap_period_idx = mid
                break

            if len(parsed_period) > 1 and req_date > period_date:  # This is a period, so look at both dates
                duration = self.parse_iso8601_duration(parsed_period[2])
                if duration:
                    end_date = datetime.fromisoformat(parsed_period[1].replace('Z', '+00:00')).replace(tzinfo=None)
                    snap_date = self.get_snap_date(
                        period_date, req_date, end_date, duration, snap_to_previous
                    )
                    snap_period_idx = mid

            if req_date < period_date:
                right = mid - 1
            else:
                left = mid + 1

        return snap_date, snap_period_idx
    
    # Trim to the specified number of periods and skip periods as needed
    def apply_skip_limit(self, layer_datetime_info: Dict, skip: int, specified_limit: Optional[int]) -> Dict:
        """Apply skip and limit to layer datetime info."""
        for key, value in layer_datetime_info.items():
            periods = value.get("periods", [])
            limit = specified_limit if specified_limit is not None else len(periods)
            
            if skip >= len(periods):
                layer_datetime_info[key]["periods"] = []
            elif len(periods) > abs(limit) or (skip > 0 and len(periods) >= skip):
                truncated = []
                if limit < 0:
                    start_idx = len(periods) + limit - skip
                    end_idx = len(periods) - skip
                    for i in range(max(0, start_idx), max(0, end_idx)):
                        if i < len(periods):
                            truncated.append(periods[i])
                else:
                    start_idx = skip
                    end_idx = min(limit + skip, len(periods))
                    truncated = periods[start_idx:end_idx]
                layer_datetime_info[key]["periods"] = truncated
                
        return layer_datetime_info
    
    """
    Conventions in this function: string date objects are passed in, but I convert to datetime objects
    filtered periods is an array of datestrings similar to all_periods
    """
    def range_handler(
        self,
        all_periods: List[str],
        default: Optional[str] = None,
        periods_start: Optional[str] = None,
        periods_end: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """Handle date range filtering."""
        periods_start_date = None
        periods_end_date = None

        if periods_start:
            try:
                periods_start_date = datetime.fromisoformat(periods_start.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                pass

        if periods_end:
            try:
                periods_end_date = datetime.fromisoformat(periods_end.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                pass

        if not all_periods:
            return default or "", []

        # Get first and last period dates
        first_period_start_date = None
        last_period_end_date = None

        try:
            first_period_start_date = len(all_periods) > 0 and datetime.fromisoformat(all_periods[0].split("/")[0].replace('Z', '+00:00')).replace(tzinfo=None) or None
            last_period_end_date = len(all_periods) > 0 and datetime.fromisoformat(all_periods[-1].split("/")[1].replace('Z', '+00:00')).replace(tzinfo=None) or None
        except (ValueError, IndexError):
            pass
        
        # Check if there's any data in the range
        if ((periods_start_date and last_period_end_date and periods_start_date > last_period_end_date) or
            (periods_end_date and first_period_start_date and periods_end_date < first_period_start_date)):
            return "", []
        
        # Find start and end indices
        start_snap_period_idx = 0
        end_snap_period_idx = len(all_periods) - 1
        start_snap_date = None
        end_snap_date = None
        
        if periods_start_date:
            if first_period_start_date and periods_start_date <= first_period_start_date:
                start_snap_period_idx = 0
            else:
                start_snap_date, start_snap_period_idx = self.time_snap(periods_start_date, all_periods, False)
                # if the periods start date doesn't fall within a period, then we need to skip the period that was last examined
                if start_snap_date is None and len(all_periods) > 1:
                    start_snap_period_idx = start_snap_period_idx + 1
                
        if periods_end_date:
            end_snap_date, end_snap_period_idx = self.time_snap(periods_end_date, all_periods, True)
        
        # Filter periods

        # Ensure that there's data between periods_start and periods_end.
        # The start snap date taking place after end snap date would mean that there's no data within the bounds.
        filtered_periods = []
        if not (start_snap_date and end_snap_date and start_snap_date > end_snap_date):
            # trim the list of periods so that the period in which we found the snap date starts with the snap date
            filtered_periods = all_periods[start_snap_period_idx:end_snap_period_idx + 1]

            # Update the filtered periods based on the requested periods start/end 
            if start_snap_date:
                if not isinstance(start_snap_date, datetime):
                    print("ERROR: periods_start is not a datetime object")
                parsed_period = filtered_periods[0].split("/")
                if start_snap_date.hour > 0 or start_snap_date.minute > 0 or start_snap_date.second > 0:
                    start_snap_date_string = start_snap_date.strftime(self.DATETIME_FORMAT)
                else:
                    start_snap_date_string = start_snap_date.strftime(self.DATE_FORMAT)
                filtered_periods[0] = start_snap_date_string + "/" + parsed_period[1] + "/" + parsed_period[2]
            if end_snap_date:
                if not isinstance(end_snap_date, datetime):
                    print("ERROR: periods_end is not a datetime object")
                
                parsed_period = filtered_periods[-1].split("/")
                if end_snap_date.hour > 0 or end_snap_date.minute > 0 or end_snap_date.second > 0:
                    end_snap_date_string = end_snap_date.strftime(self.DATETIME_FORMAT)
                else:
                    end_snap_date_string = end_snap_date.strftime(self.DATE_FORMAT)
                filtered_periods[-1] = parsed_period[0] + "/" + end_snap_date_string + "/" + parsed_period[2]
        
        # Update default to be within range
        if filtered_periods and default:
            try:
                default_date = datetime.fromisoformat(default.replace('Z', '+00:00')).replace(tzinfo=None)
                last_filtered_period_end_date = datetime.fromisoformat(filtered_periods[-1].split("/")[1].replace('Z', '+00:00')).replace(tzinfo=None)
                first_filtered_period_start_date = datetime.fromisoformat(filtered_periods[0].split("/")[0].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if default_date > last_filtered_period_end_date:
                    default = filtered_periods[-1].split("/")[1]
                elif default_date < first_filtered_period_start_date:
                    default = filtered_periods[0].split("/")[0]
            except (ValueError, IndexError):
                pass
        elif not filtered_periods:
            default = ""
            
        return default or "", filtered_periods
    
    def redis_handler(self, options: Dict[str, Any]) -> callable:
        """Create Redis handler function."""
        # Detect cluster mode from options
        cluster_mode = options.get("cluster_mode", False)

        if cluster_mode:
            # Use RedisCluster for cluster mode
            from redis.cluster import RedisCluster
            client = RedisCluster(
                host=options["host"],
                port=options.get("port", 6379),
                decode_responses=True,  # Automatically decode bytes to strings
                skip_full_coverage_check=False,  # Ensure all hash slots are covered
                read_from_replicas=True,  # Distribute reads across replicas
                reinitialize_steps=10,  # Auto-reconnect on topology changes
            )
            print(f"INFO: Redis Cluster mode enabled for host {options['host']}")
        else:
            # Use standard Redis client for single instance
            client = redis.Redis(
                host=options["host"],
                port=options.get("port", 6379),
                decode_responses=True,  # Automatically decode bytes to strings
                socket_keepalive=True,  # Keep connections alive
                socket_connect_timeout=10,  # Connection timeout
                health_check_interval=30  # Check connection health every 30s
            )
            print(f"INFO: Redis single instance mode for host {options['host']}")
        
        def handler(uuid: str, layer_name: Optional[str] = None, lookup_keys: Optional[List[str]] = None,
                   snap_date_string: Optional[str] = None, periods_start: Optional[str] = None,
                   periods_end: Optional[str] = None) -> Union[str, Dict]:

            start_db_request = time.time() * 1000 * 1000
            prefix_string = ""

            if lookup_keys:
                prefix_string = ":".join(lookup_keys) + ":"
                
            try:
                if layer_name:
                    if snap_date_string:
                        # Get best layer name
                        best_layer_name = client.hget(f"{prefix_string}layer:{layer_name}:best", snap_date_string)
                        return best_layer_name if best_layer_name else layer_name
                    else:
                        # Get default and periods
                        default = client.get(f"{prefix_string}layer:{layer_name}:default")
                        
                        key_type = client.type(f"{prefix_string}layer:{layer_name}:periods")
                        periods = None
                        
                        if key_type == "zset":
                            periods = client.zrange(f"{prefix_string}layer:{layer_name}:periods", 0, -1)
                        elif key_type == "set":
                            periods = list(client.smembers(f"{prefix_string}layer:{layer_name}:periods"))
                            periods.sort() 
                        
                        # Handle Case of Data is legitimately missing 
                        if not periods or len(periods) == 0:
                            return {"err_msg": "Invalid Layer"}
                            
                        # Process periods
                        if periods_start or periods_end:
                            default, periods = self.range_handler(periods, default, periods_start, periods_end)
                            
                        return {
                            layer_name: {
                                "default": default,
                                "periods": periods,
                                "periods_in_range": len(periods)
                            }
                        }
                else:
                    # Get all layers
                    return self.redis_get_all_layers(client, prefix_string, periods_start, periods_end)
                    
            except Exception as e:
                print(f"ERROR querying Redis: {e}")
                return self.send_response(503, json.dumps({"err_msg": "Time database error"}))
            finally:
                duration = int(time.time() * 1000 * 1000 - start_db_request)
                print(f"step=time_database_request duration={duration} uuid={uuid}")
                
        return handler
    
    def redis_get_all_layers(self, client, prefix_string: str, periods_start: Optional[str],
                           periods_end: Optional[str]) -> Dict:
        """Get all layers from Redis (supports both single instance and cluster mode)."""
        layers = {}

        # Check if client is a cluster by looking for cluster-specific methods
        is_cluster = hasattr(client, 'get_nodes')

        if is_cluster:
            # Cluster mode: scan all primary nodes
            print("INFO: Scanning Redis cluster for layers")
            try:
                # Get all primary nodes from the cluster
                nodes = client.get_nodes()
                for node in nodes:
                    # Only scan primary nodes (not replicas)
                    if node.server_type == 'primary':
                        print(f"INFO: Scanning node {node.name} (primary)")
                        cursor = 0
                        while True:
                            # Use scan_iter on the node's connection for efficiency
                            cursor, keys = node.redis_connection.scan(
                                cursor,
                                match=f"{prefix_string}layer:*",
                                count=1000  # Batch size for efficiency
                            )

                            self._process_layer_keys(client, keys, prefix_string, periods_start,
                                                    periods_end, layers)

                            if cursor == 0:
                                break
            except Exception as e:
                print(f"ERROR scanning Redis cluster: {e}")
                # Fall back to regular scan if cluster scan fails
                print("INFO: Falling back to regular SCAN (may miss keys in multi-node cluster)")
                cursor = 0
                while True:
                    cursor, keys = client.scan(cursor, match=f"{prefix_string}layer:*")
                    self._process_layer_keys(client, keys, prefix_string, periods_start,
                                            periods_end, layers)
                    if cursor == 0:
                        break
        else:
            # Single instance mode: use regular scan
            print("INFO: Scanning single Redis instance for layers")
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=f"{prefix_string}layer:*")
                self._process_layer_keys(client, keys, prefix_string, periods_start,
                                        periods_end, layers)
                if cursor == 0:
                    break

        return layers

    def _process_layer_keys(self, client, keys: List[str], prefix_string: str,
                           periods_start: Optional[str], periods_end: Optional[str],
                           layers: Dict) -> None:
        """Process Redis keys and extract layer information."""
        for key in keys:
            key_parts = key.split(":")
            if len(key_parts) >= 2:
                layer_name = key_parts[-2]
                if layer_name not in layers:
                    layers[layer_name] = {}

                default = client.get(f"{prefix_string}layer:{layer_name}:default")
                key_type = client.type(f"{prefix_string}layer:{layer_name}:periods")

                periods = []
                if key_type == "zset":
                    periods = client.zrange(f"{prefix_string}layer:{layer_name}:periods", 0, -1)
                elif key_type == "set":
                    periods = list(client.smembers(f"{prefix_string}layer:{layer_name}:periods"))
                    if periods:
                        periods.sort()

                # Always include the layer, even if periods is empty
                if periods_start or periods_end:
                    default, periods = self.range_handler(periods, default, periods_start, periods_end)

                layer_info = {
                    "periods": periods,
                    "periods_in_range": len(periods)
                }
                if default is not None:
                    layer_info["default"] = default

                layers[layer_name] = layer_info
    
    def basic_date_formatter(self, options: Optional[Dict] = None) -> callable:
        """Basic date formatter."""
        def formatter(layer_name: str, date_obj: datetime) -> str:
            # Static layer hack
            if date_obj.year <= 1900 or date_obj.year >= 2899:
                return layer_name
            else:
                return f"{layer_name}-{date_obj.strftime(self.DATETIME_FILENAME_FORMAT)}"
        return formatter
    
    def hash_formatter(self, options: Optional[Dict] = None) -> callable:
        """Hash-based filename formatter."""
        def formatter(layer_name: str, date_obj: datetime) -> str:
            date_string = date_obj.strftime(self.DATETIME_FILENAME_FORMAT)
            base_filename_string = f"{layer_name}-{date_string}"
            hash_obj = hashlib.md5(base_filename_string.encode())
            hash_str = hash_obj.hexdigest()[:4]
            return f"{hash_str}-{layer_name}-{date_string}"
        return formatter
    
    def strftime_formatter(self, options: Dict) -> callable:
        """Custom strftime formatter."""
        format_str = options.get("format_str", self.DATETIME_FILENAME_FORMAT)
        
        def formatter(layer_name: str, date_obj: datetime) -> str:
            return f"{layer_name}{date_obj.strftime(format_str)}"
        return formatter
    
    def time_service(self, layer_handler_options: Dict, filename_options: Optional[Dict] = None) -> callable:
        """Main time service handler factory."""
        # Create layer handler
        if layer_handler_options["handler_type"] == "redis":
            layer_handler = self.redis_handler(layer_handler_options)
        else:
            raise ValueError(f"Unsupported handler type: {layer_handler_options['handler_type']}")
        
        # Create filename handler
        if not filename_options:
            filename_handler = self.basic_date_formatter()
        elif filename_options.get("filename_format") == "hash":
            filename_handler = self.hash_formatter(filename_options)
        elif filename_options.get("filename_format") == "strftime":
            filename_handler = self.strftime_formatter(filename_options)
        else:
            filename_handler = self.basic_date_formatter(filename_options)
        
        def handler(query_string: str, headers: Dict[str, str], notes: Dict[str, str]) -> Tuple[str, Dict[str, str], int]:
            """Main request handler."""
            uuid = headers.get("UUID", "none")
            start_timestamp = time.time() * 1000 * 1000
            
            layer_name = self.get_query_param("layer", query_string)
            periods_start = self.get_query_param("periods_start", query_string)
            periods_end = self.get_query_param("periods_end", query_string)
            limit = self.get_query_param("limit", query_string)
            skip = int(self.get_query_param("skip", query_string) or "0")
            lookup_keys = self.get_query_keys(query_string)
            
            # Validate inputs 
            if limit:
                try:
                    limit = int(limit)
                except ValueError:
                    return self.send_response(200, json.dumps({"err_msg": "Limit must be an integer"}))
            
            if periods_start:
                try:
                    if not re.match(self.DATE_TEMPLATE, periods_start) and not re.match(self.DATETIME_TEMPLATE, periods_start):
                        return self.send_response(200, json.dumps({"err_msg": "Invalid periods start date"}))
                    datetime.fromisoformat(periods_start.replace('Z', '+00:00')).replace(tzinfo=None)
                except ValueError:
                    return self.send_response(200, json.dumps({"err_msg": "Invalid periods start date"}))
                
            if periods_end:
                try:
                    if not re.match(self.DATE_TEMPLATE, periods_end) and not re.match(self.DATETIME_TEMPLATE, periods_end):
                        return self.send_response(200, json.dumps({"err_msg": "Invalid periods end date"}))
                    datetime.fromisoformat(periods_end.replace('Z', '+00:00')).replace(tzinfo=None)
                except ValueError:
                    return self.send_response(200, json.dumps({"err_msg": "Invalid periods end date"}))
            
            # A blank query returns the entire list of layers and periods
            if not query_string or not layer_name:
                # use int to round to the nearest integer to prevent "number has no integer representation" error
                duration = int(time.time() * 1000 * 1000 - start_timestamp)
                print(f"step=timesnap_request duration={duration} uuid={uuid}")
                
                layer_datetime_info = layer_handler(uuid, None, lookup_keys, None, periods_start, periods_end)
                if limit or skip > 0:
                    layer_datetime_info = self.apply_skip_limit(layer_datetime_info, skip, limit)
                return self.send_response(200, json.dumps(layer_datetime_info))
            
            request_date_string = self.get_query_param("datetime", query_string)
            layer_datetime_info = layer_handler(uuid, layer_name, lookup_keys, None, periods_start, periods_end)
            if isinstance(layer_datetime_info, dict) and layer_datetime_info.get("err_msg"):
                return self.send_response(200, json.dumps(layer_datetime_info))
            
            # A layer but no date returns the default date and available periods for that layer
            if not request_date_string:
                # use int to round to the nearest integer to prevent "number has no integer representation" error
                duration = int(time.time() * 1000 * 1000 - start_timestamp)
                print(f"step=timesnap_request duration={duration} uuid={uuid}")
                
                if limit or skip > 0:
                    layer_datetime_info = self.apply_skip_limit(layer_datetime_info, skip, limit)
                return self.send_response(200, json.dumps(layer_datetime_info))
            
            # If it's a default request, return the default date, best layer name, and filename
            if request_date_string.lower() == "default":
                default_date_str = layer_datetime_info[layer_name]["default"]
                default_date = datetime.fromisoformat(default_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                best_layer_name = layer_handler(uuid, layer_name, lookup_keys, default_date.strftime(self.DATETIME_FORMAT))
                
                out_msg = {
                    "prefix": best_layer_name,
                    "date": default_date.strftime(self.DATETIME_FORMAT),
                    "filename": filename_handler(best_layer_name, default_date)
                }
                
                duration = int(time.time() * 1000 * 1000 - start_timestamp)
                print(f"step=timesnap_request duration={duration} uuid={uuid}")
                return self.send_response(200, json.dumps(out_msg))
            
            # Send error message if date is in a bad format
            if not re.match(self.DATE_TEMPLATE, request_date_string) and not re.match(self.DATETIME_TEMPLATE, request_date_string):
                duration = int(time.time() * 1000 * 1000 - start_timestamp)
                print(f"step=timesnap_request duration={duration} uuid={uuid}")
                return self.send_response(200, json.dumps({"err_msg": "Invalid Date"}))
            
            # Send error message if we can't parse the date for any other reason
            try:
                req_date = datetime.fromisoformat(request_date_string.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                duration = int(time.time() * 1000 * 1000 - start_timestamp)
                print(f"step=timesnap_request duration={duration} uuid={uuid}")
                return self.send_response(200, json.dumps({"err_msg": "Invalid Date"}))
            
            # Find snap date if date request is valid
            if layer_name not in layer_datetime_info:
                return self.send_response(200, json.dumps({"err_msg": "Invalid Layer"}))
                
            periods = layer_datetime_info[layer_name]["periods"]
            snap_date, _ = self.time_snap(req_date, periods, True)
            
            # Return snap date and error if none is found
            if snap_date:
                snap_date_string = snap_date.strftime(self.DATETIME_FORMAT)
                best_layer_name = layer_handler(uuid, layer_name, lookup_keys, snap_date_string)
                
                out_msg = {
                    "prefix": best_layer_name,
                    "date": snap_date_string,
                    "filename": filename_handler(best_layer_name, snap_date)
                }
            else:
                out_msg = {"err_msg": "Date out of range"}
            
            duration = int(time.time() * 1000 * 1000 - start_timestamp)
            print(f"step=timesnap_request duration={duration} uuid={uuid}")
            return self.send_response(200, json.dumps(out_msg))
        
        return handler


# For backwards compatibility
onearthTimeService = OnearthTimeService()