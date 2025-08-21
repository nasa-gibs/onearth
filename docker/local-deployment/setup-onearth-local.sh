#!/bin/bash

# OnEarth Local Setup Script
# Unified setup for serving MRF data from any projection(s) locally
# Automatically discovers your projections and configurations

set -e

# Detect script location and set up paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Check if we're in the docker/local-deployment directory or project root
if [[ "$SCRIPT_DIR" == */docker/local-deployment ]]; then
    # Script is in docker/local-deployment, paths are relative to this directory
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    DEPLOYMENT_DIR="$SCRIPT_DIR"
    VERSION_FILE="$PROJECT_ROOT/version.sh"
else
    # Script is being run from project root (e.g., ./docker/local-deployment/setup-onearth-local.sh)
    PROJECT_ROOT="$SCRIPT_DIR"
    DEPLOYMENT_DIR="$SCRIPT_DIR/docker/local-deployment"
    VERSION_FILE="$PROJECT_ROOT/version.sh"
    # Change to deployment directory for relative paths to work
    cd "$DEPLOYMENT_DIR"
fi

# Set default directory paths (always relative to deployment directory)
DEFAULT_MRF_ARCHIVE_DIR="$DEPLOYMENT_DIR/local-mrf-archive"
DEFAULT_SHP_ARCHIVE_DIR="$DEPLOYMENT_DIR/local-shp-archive"
DEFAULT_CONFIG_DIR="$DEPLOYMENT_DIR/onearth-configs"
MRF_ARCHIVE_DIR="${MRF_ARCHIVE_DIR:-local-mrf-archive}"
SHP_ARCHIVE_DIR="${SHP_ARCHIVE_DIR:-local-shp-archive}"
CONFIG_DIR="${CONFIG_DIR:-onearth-configs}"

# Parse command line arguments
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -m, --mrf-archive DIR     MRF archive directory (default: local-mrf-archive)"
    echo "  -p, --shp-archive DIR     SHP archive directory (default: local-shp-archive)"
    echo "  -c, --config DIR          Configuration directory (default: onearth-configs)"
    echo "  -b, --force-build-all     Force rebuild all Docker images"
    echo "  --build-deps              Force rebuild only dependencies (onearth-deps)"
    echo "  -s, --service SERVICES    Rebuild only the specified service(s) (space-separated)"
    echo "  --no-build               Skip building, only start existing images"
    echo "  --teardown               Stop and remove all OnEarth containers and networks"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Build behavior:"
    echo "  Default: Only build missing images (fastest for existing setups)"
    echo "  --force-build-all: Force rebuild all images (slower, but ensures latest code)"
    echo "  --build-deps: Only rebuild base dependencies (useful after system updates)"
    echo "  --service: Rebuild only specific service(s)"
    echo "  --no-build: Start services without building (fastest, requires existing images)"
    echo "  --teardown: Completely stop and remove all OnEarth containers and networks"
    echo ""
    echo "Available services for --service:"
    echo "  deps, time-service, tile-services, capabilities, reproject, wms, demo"
    echo ""
    echo "Examples:"
    echo "  $0                        # Smart build - only build missing images"
    echo "  $0 --force-build-all      # Force rebuild everything"
    echo "  $0 --no-build             # Start without building (fastest)"
    echo "  $0 --build-deps           # Only rebuild dependencies"
    echo "  $0 --service tile-services # Rebuild just tile-services"
    echo "  $0 --service \"tile-services capabilities\" # Rebuild multiple services"
    echo "  $0 -m my-data -c my-configs --service \"wms reproject\""
    echo "  $0 --teardown             # Stop and remove all OnEarth containers"
    exit 1
}

FORCE_BUILD=false
BUILD_DEPS_ONLY=false
BUILD_SERVICE=""
NO_BUILD=false
TEARDOWN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mrf-archive)
            MRF_ARCHIVE_DIR="$2"
            shift 2
            ;;
        -p|--shp-archive)
            SHP_ARCHIVE_DIR="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -b|--force-build-all)
            FORCE_BUILD=true
            shift
            ;;
        --build-deps)
            BUILD_DEPS_ONLY=true
            shift
            ;;
        -s|--service)
            BUILD_SERVICE="$2"
            shift 2
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --teardown)
            TEARDOWN=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        -*)
            echo "Unknown option $1"
            show_usage
            ;;
        *)
            echo "Unknown argument $1"
            show_usage
            ;;
    esac
done

# Resolve directory paths - if using defaults, use absolute paths
if [ "$MRF_ARCHIVE_DIR" = "local-mrf-archive" ]; then
    MRF_ARCHIVE_DIR="$DEFAULT_MRF_ARCHIVE_DIR"
fi
if [ "$SHP_ARCHIVE_DIR" = "local-shp-archive" ]; then
    SHP_ARCHIVE_DIR="$DEFAULT_SHP_ARCHIVE_DIR"
fi
if [ "$CONFIG_DIR" = "onearth-configs" ]; then
    CONFIG_DIR="$DEFAULT_CONFIG_DIR"
fi

# Handle teardown option
if [ "$TEARDOWN" = true ]; then
    echo "=========================================="
    echo "OnEarth Teardown"
    echo "=========================================="
    echo ""
    echo "🧹 Stopping and removing OnEarth containers..."
    
    # Stop and remove containers (try both old and new project names for cleanup)
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" down --remove-orphans 2>/dev/null || true
    
    # Also try to stop any containers that might be running from old run.sh script
    echo "🔍 Checking for any remaining OnEarth containers..."
    ONEARTH_CONTAINERS=$(docker ps -a --filter "name=onearth" --format "{{.Names}}" 2>/dev/null || true)
    
    if [ -n "$ONEARTH_CONTAINERS" ]; then
        echo "   Found containers: $ONEARTH_CONTAINERS"
        echo "   Stopping and removing..."
        echo "$ONEARTH_CONTAINERS" | xargs -r docker rm -f 2>/dev/null || true
    else
        echo "   No additional OnEarth containers found"
    fi
    
    # Remove OnEarth networks
    echo "🌐 Removing OnEarth networks..."
    docker network rm oe2 2>/dev/null || true
    docker network rm onearth_oe2 2>/dev/null || true
    
    # Clean up unused volumes
    echo "🧽 Cleaning up unused Docker resources..."
    docker system prune -f --volumes 2>/dev/null || true
    
    echo ""
    echo "✅ Teardown complete!"
    echo ""
    echo "All OnEarth containers, networks, and unused volumes have been removed."
    echo "To start fresh, run: $0"
    echo ""
    exit 0
fi

echo "=========================================="
echo "OnEarth Local Setup"
echo "=========================================="
echo ""
echo "📁 Using directories:"
echo "   MRF Archive: $MRF_ARCHIVE_DIR"
echo "   SHP Archive: $SHP_ARCHIVE_DIR"
echo "   Configurations: $CONFIG_DIR"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required directories exist
if [ ! -d "$MRF_ARCHIVE_DIR" ]; then
    echo "❌ Error: $MRF_ARCHIVE_DIR directory not found"
    echo "   Please organize your MRF data by projection (e.g., $MRF_ARCHIVE_DIR/epsg4326/)"
    exit 1
fi

if [ ! -d "$SHP_ARCHIVE_DIR" ]; then
    echo "⚠️ Warning: $SHP_ARCHIVE_DIR directory not found"
    echo "   Please that $SHP_ARCHIVE_DIR exists or specify a different directory with -p if you intend to serve vectors via WMS, otherwise this will be ignored."
    echo ""
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Error: $CONFIG_DIR directory not found"
    echo "   Please run: ./generate-configs.sh -m $MRF_ARCHIVE_DIR -t $CONFIG_DIR <projection>"
    exit 1
fi

echo "✅ Docker is running"
echo "✅ Local MRF archive found"
if [ ! -d "$SHP_ARCHIVE_DIR" ]; then
    echo "⚠️ Local SHP archive not found, vectors will not be served via WMS"
else
    echo "✅ Local SHP archive found"
fi
echo "✅ Local OnEarth configs found"

# Validate service names if specified
if [ -n "$BUILD_SERVICE" ]; then
    echo "🔍 Validating service name(s)..."
    # Convert space-separated services to array
    IFS=' ' read -ra SERVICES <<< "$BUILD_SERVICE"
    for service in "${SERVICES[@]}"; do
        case "$service" in
            deps|time-service|tile-services|capabilities|reproject|wms|demo)
                echo "   ✅ Service '$service' is valid"
                ;;
            *)
                echo "   ❌ Error: Invalid service '$service'"
                echo "   Valid services: deps, time-service, tile-services, capabilities, reproject, wms, demo"
                exit 1
                ;;
        esac
    done
fi

# Source version and set environment variables
echo "📝 Setting up environment variables..."
source "$VERSION_FILE"

export DOCKER_PLATFORM_OPTION=$(uname -m | grep -qE 'aarch64|arm64' && echo "linux/amd64" || echo "")
export USE_SSL=false  # Disable SSL for local development
export SERVER_NAME=localhost
export DEBUG_LOGGING=true  # Enable debug logging for local development
export MRF_ARCHIVE_DIR  # Export for docker-compose to use
export SHP_ARCHIVE_DIR  # Export for docker-compose to use
export CONFIG_DIR  # Export for docker-compose to use
export ONEARTH_DEPS_TAG=nasagibs/onearth-deps:${ONEARTH_VERSION}
export START_ONEARTH_TOOLS_CONTAINER=0

echo "   ONEARTH_VERSION: $ONEARTH_VERSION"
echo "   ONEARTH_RELEASE: $ONEARTH_RELEASE"
echo "   USE_SSL: $USE_SSL"
echo "   SERVER_NAME: $SERVER_NAME"
echo "   DEBUG_LOGGING: $DEBUG_LOGGING"
echo "   MRF_ARCHIVE_DIR: $MRF_ARCHIVE_DIR"
echo "   SHP_ARCHIVE_DIR: $SHP_ARCHIVE_DIR"

# Discover available projections from MRF archive
echo "🔍 Discovering available projections..."
PROJECTIONS=()
if [ -d "$MRF_ARCHIVE_DIR" ]; then
    for proj_dir in "$MRF_ARCHIVE_DIR"/*/; do
        if [ -d "$proj_dir" ]; then
            proj_name=$(basename "$proj_dir")
            PROJECTIONS+=("$proj_name")
            echo "   Found projection: $proj_name"
        fi
    done
fi

if [ ${#PROJECTIONS[@]} -eq 0 ]; then
    echo "❌ Error: No projection directories found in $MRF_ARCHIVE_DIR/"
    echo "   Expected structure: $MRF_ARCHIVE_DIR/epsg4326/, $MRF_ARCHIVE_DIR/epsg3857/, etc."
    exit 1
fi

# Discover available endpoints from configs
echo "🔍 Discovering configured endpoints..."
ENDPOINTS=()
if [ -d "$CONFIG_DIR/config/endpoint" ]; then
    for endpoint_file in "$CONFIG_DIR/config/endpoint"/*.yaml; do
        if [ -f "$endpoint_file" ]; then
            endpoint_name=$(basename "$endpoint_file" .yaml)
            ENDPOINTS+=("$endpoint_name")
            echo "   Found endpoint: $endpoint_name"
        fi
    done
fi

if [ ${#ENDPOINTS[@]} -eq 0 ]; then
    echo "❌ Error: No endpoint configurations found in $CONFIG_DIR/config/endpoint/"
    echo "   Please create endpoint YAML files for each projection you want to serve"
    echo "   Run: ./generate-configs.sh -m $MRF_ARCHIVE_DIR -p $SHP_ARCHIVE_DIR -t $CONFIG_DIR <projection>"
    exit 1
fi

# Display discovered layers by projection
echo "🔍 Discovering available layers..."
TOTAL_LAYERS=0
for proj in "${PROJECTIONS[@]}"; do
    echo "   📂 $proj data:"
    if [ -d "$MRF_ARCHIVE_DIR/$proj" ]; then
        layer_count=0
        for layer_dir in "$MRF_ARCHIVE_DIR/$proj"/*/; do
            if [ -d "$layer_dir" ]; then
                layer_name=$(basename "$layer_dir")
                echo "      • $layer_name"
                ((layer_count++))
                ((TOTAL_LAYERS++))
            fi
        done
        if [ $layer_count -eq 0 ]; then
            echo "      (No layer directories found)"
        fi
    fi
    
    # Check for corresponding layer configs
    layer_config_dir="$CONFIG_DIR/config/layers/$proj"
    if [ -d "$layer_config_dir" ]; then
        config_count=$(find "$layer_config_dir" -name "*.yaml" 2>/dev/null | wc -l)
        echo "   📝 $proj configs: $config_count layer configuration(s)"
    else
        echo "   📝 $proj configs: No configuration directory found"
    fi
done

echo ""
echo "📊 Summary:"
echo "   • ${#PROJECTIONS[@]} projection(s): ${PROJECTIONS[*]}"
echo "   • ${#ENDPOINTS[@]} endpoint(s): ${ENDPOINTS[*]}"
echo "   • $TOTAL_LAYERS total layer(s) discovered"

# Create certificates directory if it doesn't exist
CERTS_DIR="$PROJECT_ROOT/certs"
if [ ! -d "$CERTS_DIR" ]; then
    echo "📁 Creating certs directory..."
    mkdir -p "$CERTS_DIR"
fi

# Stop any existing containers
echo "🛑 Stopping any existing OnEarth containers..."
docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" down 2>/dev/null || true

# Build logic based on options
if [ "$NO_BUILD" = true ]; then
    echo "⚡ Skipping build, starting existing images..."
elif [ "$BUILD_DEPS_ONLY" = true ]; then
    echo "🏗️  Rebuilding dependencies only..."
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" build onearth-deps
elif [ -n "$BUILD_SERVICE" ]; then
    # Convert space-separated services to array
    IFS=' ' read -ra SERVICES <<< "$BUILD_SERVICE"
    if [ ${#SERVICES[@]} -eq 1 ]; then
        echo "🏗️  Rebuilding service '${SERVICES[0]}' only..."
    else
        echo "🏗️  Rebuilding ${#SERVICES[@]} services: $BUILD_SERVICE"
    fi
    
    # Build each specified service
    SERVICE_NAMES=()
    for service in "${SERVICES[@]}"; do
        # Map friendly names to actual service names
        case "$service" in
            deps)
                SERVICE_NAMES+=("onearth-deps")
                ;;
            *)
                SERVICE_NAMES+=("onearth-$service")
                ;;
        esac
    done
    
    # Build all specified services
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" build "${SERVICE_NAMES[@]}"
elif [ "$FORCE_BUILD" = true ]; then
    echo "🏗️  Force rebuilding all Docker images (this may take several minutes)..."
    echo "    Building dependencies..."
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" build onearth-deps
    echo "    Building core services..."
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" build onearth-time-service onearth-capabilities onearth-tile-services onearth-reproject onearth-wms
    echo "    Building demo interface..."
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" build onearth-demo
else
    echo "🏗️  Smart build - only building missing images..."
    # Let docker compose decide what needs building (no --build flag)
fi

echo "🚀 Starting OnEarth services..."
if [ "$NO_BUILD" = true ]; then
    # Check if required images exist
    echo "   Checking for required images..."
    REQUIRED_TAG="${ONEARTH_VERSION}-${ONEARTH_RELEASE}"
    MISSING_IMAGES=0
    
    for service in capabilities time-service tile-services reproject wms demo; do
        if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "nasagibs/onearth-${service}:${REQUIRED_TAG}"; then
            echo "   ⚠️  Missing: nasagibs/onearth-${service}:${REQUIRED_TAG}"
            ((MISSING_IMAGES++))
        fi
    done
    
    if [ $MISSING_IMAGES -gt 0 ]; then
        echo "   ❌ $MISSING_IMAGES required images are missing"
        echo "   💡 Run without --no-build to build them, or use --build-deps to rebuild base dependencies"
        exit 1
    fi
    
    echo "   ✅ All required images found"
    # Start without building - will fail if images don't exist
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" up -d --no-build
else
    # True smart build - only build what's missing or changed
    docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" up -d
fi

echo ""
echo "⏳ Waiting for services to become healthy..."
echo "   This may take 1-2 minutes for all services to start..."

# Wait for services to be healthy
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker compose -p onearth -f "$DEPLOYMENT_DIR/docker-compose.local.yml" ps | grep -q "unhealthy"; then
        echo "   Still starting... (attempt $((attempt + 1))/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    else
        break
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  Services are taking longer than expected to start. Check logs with:"
    echo "   docker exec [service-name] cat /var/log/onearth/config.log"
    echo "   docker exec [service-name] cat /var/log/httpd/error_log"
else
    echo "✅ All services are running!"
fi

echo ""
echo "=========================================="
echo "🎉 OnEarth Local Setup Complete!"
echo "=========================================="
echo ""

# Display service access points
echo "🌐 Your OnEarth Services:"
echo ""
echo "📊 Demo Interface:"
echo "   http://localhost"
echo ""

echo "🔧 Individual Services:"
echo "   • Tile Services:    https://localhost (port 443)"
echo "   • Capabilities:      http://localhost:8081"
echo "   • Reproject:         http://localhost:8082"
echo "   • WMS Service:       https://localhost:8443"
echo "   • Time Service:      Redis on port 6379"
echo ""

echo "📋 Viewing Logs:"
echo "   OnEarth config logs:  docker exec [service-name] cat /var/log/onearth/config.log"
echo "   Apache error logs:    docker exec [service-name] cat /var/log/httpd/error_log"
echo "   WMS MapServer logs:   docker exec [service-name] cat /var/log/mapserver/error.log"
echo "   Demo container logs:  docker exec [service-name] cat /var/log/httpd/error_log"
echo ""

echo "📝 Testing Your Setup:"
echo "   # Interactive demo page with all endpoints"
echo "   http://localhost/demo/"
echo ""

echo "🔍 If you encounter issues:"
echo "   1. Check OnEarth config logs: docker exec [service-name] cat /var/log/onearth/config.log"
echo "   2. Check Apache error logs: docker exec [service-name] cat /var/log/httpd/error_log"
echo "   3. Check WMS MapServer logs: docker exec onearth-wms cat /var/log/mapserver/error.log"
echo "   4. Verify MRF files are accessible in $MRF_ARCHIVE_DIR/{projection}/"
echo "   5. Ensure layer configs exist in $CONFIG_DIR/config/layers/{projection}/"
echo "   6. Run: ./generate-configs.sh -m $MRF_ARCHIVE_DIR -p $SHP_ARCHIVE_DIR -t $CONFIG_DIR <projection>"
echo ""

echo "🚀 Quick validation:"
echo "   find $MRF_ARCHIVE_DIR -name '*.mrf' | head -5  # Check MRF files"
echo "   find $CONFIG_DIR/config/layers -name '*.yaml' | head -5  # Check configs"
