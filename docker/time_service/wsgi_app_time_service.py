import sys
import os
import json
import time
import traceback

from time_service import OnearthTimeService

# Redis host configuration
REDIS_HOST = "{REDIS_HOST}"

def detect_cluster_mode(host, port=6379, timeout=10):
    """
    Auto-detect if Redis host is a cluster or single instance.

    This runs once at module import time to determine the correct connection mode.

    Args:
        host: Redis hostname or configuration endpoint
        port: Redis port (default: 6379)
        timeout: Connection timeout in seconds (default: 10)

    Returns:
        bool: True if cluster mode detected, False if single instance
    """

    print(f"INFO: Auto-detecting Redis mode")

    try:
        # Try connecting as a cluster first
        import redis
        from redis.cluster import RedisCluster

        client = RedisCluster(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=timeout,
            socket_timeout=timeout
        )

        # Test cluster connection with ping
        client.ping()

        # Check if we actually got cluster info
        cluster_info = client.cluster_info()
        if cluster_info and cluster_info.get('cluster_state') == 'ok':
            # Get node count for logging
            nodes = client.get_nodes()
            primary_count = sum(1 for node in nodes if node.server_type == 'primary')
            replica_count = sum(1 for node in nodes if node.server_type == 'replica')

            print(f"Auto-detected REDIS CLUSTER: {primary_count} primaries, {replica_count} replicas")
            client.close()
            return True
        else:
            print("INFO: Cluster connection succeeded but cluster_state not ok, trying single instance")
            client.close()
            raise Exception("Not a valid cluster")

    except Exception as cluster_error:
        # Cluster connection failed, try single instance
        print(f"INFO: Cluster detection failed ({type(cluster_error).__name__}), trying single instance...")

        try:
            import redis
            client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=timeout,
                socket_timeout=timeout
            )

            # Test single instance connection
            client.ping()

            # Verify it's not actually a cluster
            try:
                info = client.info('cluster')
                if info.get('cluster_enabled') == 1:
                    print("WARNING: Server reports cluster_enabled=1, but cluster connection failed. Using cluster mode anyway.")
                    client.close()
                    return True
            except:
                # INFO CLUSTER command not available or failed - definitely single instance
                pass

            print(f"Auto-detected SINGLE INSTANCE")
            client.close()
            return False

        except Exception as single_error:
            print(f"ERROR: Both cluster and single instance detection failed!")
            print(f"  Cluster error: {cluster_error}")
            print(f"  Single instance error: {single_error}")
            print(f"  Defaulting to single instance mode (may cause connection errors)")
            return False


# Auto-detect cluster mode once at module import time
# This runs ONCE when the WSGI app loads, not per-request
REDIS_CLUSTER_MODE = detect_cluster_mode(REDIS_HOST)
print(f"INFO: Redis connection mode set to: {'CLUSTER' if REDIS_CLUSTER_MODE else 'SINGLE INSTANCE'}")


# Create a single Redis handler at module level (initialized once when WSGI app loads)
# redis-py handles all connection pooling internally, so we don't need custom pooling
# This handler is thread-safe and can be called concurrently by multiple threads
time_service = OnearthTimeService()
_redis_handler = time_service.time_service(
    {
        "handler_type": "redis",
        "host": REDIS_HOST,
        "cluster_mode": REDIS_CLUSTER_MODE
    },
    {"filename_format": "basic"}
)


def application(environ, start_response):
    """
    WSGI application for OnEarth Time Service.

    This is the main entry point for all time service requests. The handler
    uses redis-py's built-in connection pooling, which is thread-safe and
    handles all connection management automatically.
    """
    start_time = time.time()

    try:
        # Get query string
        query_string = environ.get('QUERY_STRING', '')

        # Get headers from WSGI environ
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                headers[header_name] = value

        # Add UUID if not present (for request tracking)
        if 'UUID' not in headers:
            headers['UUID'] = 'wsgi-request'

        # Call the time service handler (redis-py handles connection pooling internally)
        response_body, response_headers, status_code = _redis_handler(query_string, headers, {})

        # Convert headers to list of tuples for WSGI
        wsgi_headers = []
        for header_name, header_value in response_headers.items():
            wsgi_headers.append((header_name, header_value))

        # Start the response
        status = f"{status_code} {'OK' if status_code == 200 else 'Error'}"
        start_response(status, wsgi_headers)

        # Log request duration
        duration_ms = (time.time() - start_time) * 1000
        print(f"step=wsgi_request duration={duration_ms:.2f}ms status={status_code} uuid={headers['UUID']}")

        # Return response body as bytes
        return [response_body.encode('utf-8')]

    except Exception as e:
        # Handle errors with detailed logging
        duration_ms = (time.time() - start_time) * 1000
        print(f"ERROR in WSGI application after {duration_ms:.2f}ms: {e}")
        traceback.print_exc()

        error_response = json.dumps({
            "err_msg": f"Server error: {str(e)}",
            "error_type": type(e).__name__
        })
        start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
        return [error_response.encode('utf-8')]
