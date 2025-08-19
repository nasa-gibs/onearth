#!/bin/bash

# Helper script to generate configuration files for OnEarth local setup
# This script creates the directory structure and configuration files needed

set -e

# Detect script location and set up paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Check if we're in the docker/local-deployment directory or project root
if [[ "$SCRIPT_DIR" == */docker/local-deployment ]]; then
    # Script is in docker/local-deployment, paths are relative to this directory
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    DEPLOYMENT_DIR="$SCRIPT_DIR"
else
    # Script is being run from project root (e.g., ./docker/local-deployment/generate-configs.sh)
    PROJECT_ROOT="$SCRIPT_DIR"
    DEPLOYMENT_DIR="$SCRIPT_DIR/docker/local-deployment"
    # Change to deployment directory for relative paths to work
    cd "$DEPLOYMENT_DIR"
fi

# Set default directory paths (always relative to deployment directory)
DEFAULT_MRF_ARCHIVE_DIR="$DEPLOYMENT_DIR/local-mrf-archive"
DEFAULT_SOURCE_CONFIG_DIR="$DEPLOYMENT_DIR/downloaded-onearth-configs"
DEFAULT_TARGET_CONFIG_DIR="$DEPLOYMENT_DIR/onearth-configs"
MRF_ARCHIVE_DIR="${MRF_ARCHIVE_DIR:-local-mrf-archive}"
SOURCE_CONFIG_DIR="${SOURCE_CONFIG_DIR:-downloaded-onearth-configs}"
TARGET_CONFIG_DIR="${TARGET_CONFIG_DIR:-onearth-configs}"

# Parse command line arguments
show_usage() {
    echo "Usage: $0 [options] [projection1] [projection2] ..."
    echo ""
    echo "Options:"
    echo "  -m, --mrf-archive DIR     MRF archive directory (default: local-mrf-archive)"
    echo "  -s, --source-config DIR   Source config directory (default: downloaded-onearth-configs)"  
    echo "  -t, --target-config DIR   Target config directory (default: onearth-configs)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "If no projections are specified, defaults to: epsg4326 epsg3857 epsg3031 epsg3413"
    echo ""
    echo "Examples:"
    echo "  $0                        # Set up all standard projections"
    echo "  $0 epsg4326               # Set up only EPSG:4326"
    echo "  $0 -m my-data -t my-configs epsg4326 epsg3857"
    echo "  $0 --mrf-archive satellite-data --target-config prod-configs"
    exit 1
}


# Parse arguments
PROJECTIONS_TO_SETUP=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mrf-archive)
            MRF_ARCHIVE_DIR="$2"
            shift 2
            ;;
        -s|--source-config)
            SOURCE_CONFIG_DIR="$2"
            shift 2
            ;;
        -t|--target-config)
            TARGET_CONFIG_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        -*)
            echo "Unknown option $1"
            show_usage
            ;;
        *)
            PROJECTIONS_TO_SETUP+=("$1")
            shift
            ;;
    esac
done

# Resolve directory paths - if using defaults, use absolute paths
if [ "$MRF_ARCHIVE_DIR" = "local-mrf-archive" ]; then
    MRF_ARCHIVE_DIR="$DEFAULT_MRF_ARCHIVE_DIR"
fi
if [ "$SOURCE_CONFIG_DIR" = "downloaded-onearth-configs" ]; then
    SOURCE_CONFIG_DIR="$DEFAULT_SOURCE_CONFIG_DIR"
fi
if [ "$TARGET_CONFIG_DIR" = "onearth-configs" ]; then
    TARGET_CONFIG_DIR="$DEFAULT_TARGET_CONFIG_DIR"
fi

# Check if projections were provided, default to all standard projections if none specified
if [ ${#PROJECTIONS_TO_SETUP[@]} -eq 0 ]; then
    PROJECTIONS_TO_SETUP=("epsg4326" "epsg3857" "epsg3031" "epsg3413")
    echo "ℹ️  No projections specified, defaulting to all standard projections: ${PROJECTIONS_TO_SETUP[*]}"
fi

echo "=========================================="
echo "OnEarth Configuration Generator"
echo "=========================================="
echo ""
echo "📁 Using directories:"
echo "   MRF Archive: $MRF_ARCHIVE_DIR"
echo "   Source Configs: $SOURCE_CONFIG_DIR"
echo "   Target Configs: $TARGET_CONFIG_DIR"
echo ""

# Function to create endpoint configs for a projection (all variants: best, std, nrt, all)
create_endpoint_configs() {
    local projection=$1
    local variants=("best" "std" "nrt" "all")
    
    echo "📝 Creating endpoint configs for $projection..."
    mkdir -p "$TARGET_CONFIG_DIR/config/endpoint"
    
    # Check if base template exists
    local base_template="$DEPLOYMENT_DIR/templates/endpoint/${projection}_template.yaml"
    if [ ! -f "$base_template" ]; then
        echo "   ⚠️  No base template found for $projection, you'll need to create endpoint configs manually"
        return
    fi
    
    for variant in "${variants[@]}"; do
        local endpoint_file="$TARGET_CONFIG_DIR/config/endpoint/${projection}_${variant}.yaml"
        
        echo "   Creating: ${projection}_${variant}.yaml"
        
        # Copy base template and substitute {{ENDPOINT}} placeholder
        sed "s/{{ENDPOINT}}/$variant/g" "$base_template" > "$endpoint_file"
        echo "   ✅ Created ${projection}_${variant}.yaml from base template"
    done
}

# Function to create variant-specific mapserver headers
create_variant_headers() {
    local projection=$1
    local variants=("best" "std" "nrt" "all")
    
    echo "📄 Creating variant-specific mapserver headers for $projection..."
    
    # Check if base header exists
    local base_header="$PROJECT_ROOT/docker/sample_configs/mapserver/${projection}.header"
    if [ ! -f "$base_header" ]; then
        echo "   ⚠️  No base header found for $projection"
        return
    fi
    
    for variant in "${variants[@]}"; do
        local variant_header="$TARGET_CONFIG_DIR/config/mapserver/${projection}_${variant}.header"
        
        # Copy base header
        cp "$base_header" "$variant_header"
        
        # Customize for variant
        local projection_upper=$(echo "${projection}" | tr '[:lower:]' '[:upper:]')
        local map_name="NASA_GIBS_${projection_upper}_${variant}"
        local wms_title="NASA Global Imagery Browse Services for EOSDIS WMS (EPSG:${projection#epsg} / ${variant})"
        local wms_onlineresource="https://gibs.earthdata.nasa.gov/wms/${projection}/${variant}/"
        
        # Update the header file with variant-specific values
        sed -i.bak "s/Name.*\".*\"/Name                  \"${map_name}\"/" "$variant_header"
        sed -i.bak "s|\"wms_title\".*\".*\"|\"wms_title\"              \"${wms_title}\"|" "$variant_header"
        sed -i.bak "s|\"wms_onlineresource\".*\".*\"|\"wms_onlineresource\"     \"${wms_onlineresource}\"|" "$variant_header"
        
        # Remove backup file
        rm -f "$variant_header.bak"
        
        echo "   ✅ Created ${projection}_${variant}.header"
    done
}

# Function to copy required configuration files for a projection
copy_projection_configs() {
    local projection=$1
    
    echo "📁 Setting up configuration files for $projection..."
    
    # Ensure mapserver directory exists
    mkdir -p "$TARGET_CONFIG_DIR/config/mapserver"
    
    # Copy essential mapserver files (symbols.sym and fonts.txt) - only once
    if [ ! -f "$TARGET_CONFIG_DIR/config/mapserver/symbols.sym" ]; then
        if [ -f "$PROJECT_ROOT/docker/wms_service/symbols.sym" ]; then
            cp "$PROJECT_ROOT/docker/wms_service/symbols.sym" "$TARGET_CONFIG_DIR/config/mapserver/"
            echo "   ✅ Copied symbols.sym"
        else
            echo "   ⚠️  symbols.sym not found in docker/wms_service/"
        fi
    fi
    
    if [ ! -f "$TARGET_CONFIG_DIR/config/mapserver/fonts.txt" ]; then
        if [ -f "$PROJECT_ROOT/docker/wms_service/fonts.txt" ]; then
            cp "$PROJECT_ROOT/docker/wms_service/fonts.txt" "$TARGET_CONFIG_DIR/config/mapserver/"
            echo "   ✅ Copied fonts.txt"
        else
            echo "   ⚠️  fonts.txt not found in docker/wms_service/"
        fi
    fi
    

    
    # Ensure conf directory exists
    mkdir -p "$TARGET_CONFIG_DIR/config/conf"
    
    # Copy tilematrixsetlimits.xml (shared configuration file) - only copy once
    if [ ! -f "$TARGET_CONFIG_DIR/config/conf/tilematrixsetlimits.xml" ]; then
        if [ -f "$PROJECT_ROOT/src/modules/gc_service/conf/tilematrixsetlimits.xml" ]; then
            cp "$PROJECT_ROOT/src/modules/gc_service/conf/tilematrixsetlimits.xml" "$TARGET_CONFIG_DIR/config/conf/"
            echo "   ✅ Copied tilematrixsetlimits.xml"
        else
            echo "   ⚠️  tilematrixsetlimits.xml not found in src/modules/gc_service/conf/"
        fi
    fi
    
    # Copy tilematrixsets.xml (if it exists) - only copy once
    if [ ! -f "$TARGET_CONFIG_DIR/config/conf/tilematrixsets.xml" ]; then
        if [ -f "$PROJECT_ROOT/src/modules/gc_service/conf/tilematrixsets.xml" ]; then
            cp "$PROJECT_ROOT/src/modules/gc_service/conf/tilematrixsets.xml" "$TARGET_CONFIG_DIR/config/conf/"
            echo "   ✅ Copied tilematrixsets.xml"
        elif [ -f "docker/sample_configs/conf/tilematrixsets.xml" ]; then
            cp "$PROJECT_ROOT/docker/sample_configs/conf/tilematrixsets.xml" "$TARGET_CONFIG_DIR/config/conf/"
            echo "   ✅ Copied tilematrixsets.xml from sample configs"
        else
            echo "   ⚠️  tilematrixsets.xml not found"
        fi
    fi
    
    # Copy and rename endpoint-specific headers
    for header_type in "header_gc" "header_gts" "header_twms_gc"; do
        source_file="$PROJECT_ROOT/docker/sample_configs/conf/${projection}_all_${header_type}.xml"
        dest_file="$TARGET_CONFIG_DIR/config/conf/${projection}_${header_type}.xml"
        
        if [ -f "$source_file" ]; then
            cp "$source_file" "$dest_file"
            echo "   ✅ Copied $header_type"
        else
            echo "   ⚠️  No $header_type found for $projection"
        fi
    done
}

# Function to create layer config directory structure and copy source configs
create_layer_structure() {
    local projection=$1
    
    echo "📂 Creating layer config structure for $projection..."
    mkdir -p "$TARGET_CONFIG_DIR/config/layers/$projection"
    echo "   ✅ Created $TARGET_CONFIG_DIR/config/layers/$projection/"
    
    # Copy any existing layer configs from source directory
    if [ -d "$SOURCE_CONFIG_DIR/config/layers/$projection" ]; then
        echo "📋 Copying existing layer configs for $projection..."
        cp -r "$SOURCE_CONFIG_DIR/config/layers/$projection/"* "$TARGET_CONFIG_DIR/config/layers/$projection/" 2>/dev/null || true
        
        # Update paths in copied configs
        find "$TARGET_CONFIG_DIR/config/layers/$projection" -name "*.yaml" -type f | while read -r config_file; do
            # Update data_file_uri to point to local archive (use direct path, not file:// URI)
            sed -i.bak "s|data_file_uri:[[:space:]]*['\"]\?.*$projection\(.*\)|data_file_uri: '/onearth/archive/$projection\1'|g" "$config_file"
            # Update idx_path FIX THIS PART FOR DELIBERATELY SPECIFIED ONES
            sed -i.bak "s|idx_path:[[:space:]]*.*$projection\(.*\)|idx_path: /onearth/idx/$projection\1|g" "$config_file"
            # Remove backup files
            rm -f "$config_file.bak"
        done
        
        config_count=$(find "$TARGET_CONFIG_DIR/config/layers/$projection" -name "*.yaml" -type f | wc -l)
        echo "   ✅ Copied and updated $config_count layer config(s)"
    else
        echo "   ℹ️  No existing configs found in $SOURCE_CONFIG_DIR/config/layers/$projection"
    fi
}

# Check if we have the required base structure
if [ ! -d "$TARGET_CONFIG_DIR/config" ]; then
    echo "📁 Creating base config structure..."
    mkdir -p "$TARGET_CONFIG_DIR/config/endpoint" "$TARGET_CONFIG_DIR/config/layers" "$TARGET_CONFIG_DIR/config/conf" "$TARGET_CONFIG_DIR/config/mapserver"
fi

# Projections are already set from command line parsing above
echo "🎯 Setting up configurations for specified projections: ${PROJECTIONS_TO_SETUP[*]}"

# Function to copy oe-status configurations (always needed for WMS healthcheck)
copy_oe_status_configs() {
    echo "🩺 Setting up oe-status endpoint for WMS healthcheck..."
    
    # Copy oe-status endpoint configurations
    if [ -f "$PROJECT_ROOT/docker/oe-status/endpoint/oe-status.yaml" ]; then
        cp "$PROJECT_ROOT/docker/oe-status/endpoint/oe-status.yaml" "$TARGET_CONFIG_DIR/config/endpoint/"
        echo "   ✅ Copied oe-status.yaml"
    else
        echo "   ⚠️  oe-status.yaml not found in docker/oe-status/endpoint/"
    fi
    
    if [ -f "$PROJECT_ROOT/docker/oe-status/endpoint/oe-status_reproject.yaml" ]; then
        cp "$PROJECT_ROOT/docker/oe-status/endpoint/oe-status_reproject.yaml" "$TARGET_CONFIG_DIR/config/endpoint/"
        echo "   ✅ Copied oe-status_reproject.yaml"
    else
        echo "   ⚠️  oe-status_reproject.yaml not found in docker/oe-status/endpoint/"
    fi
    
    # Copy oe-status layer configurations
    mkdir -p "$TARGET_CONFIG_DIR/config/layers/oe-status"
    if [ -d "$PROJECT_ROOT/docker/oe-status/layers" ]; then
        cp -r "$PROJECT_ROOT/docker/oe-status/layers/"* "$TARGET_CONFIG_DIR/config/layers/oe-status/" 2>/dev/null || true
        layer_count=$(find "$TARGET_CONFIG_DIR/config/layers/oe-status" -name "*.yaml" -type f | wc -l)
        echo "   ✅ Copied $layer_count oe-status layer config(s)"
    else
        echo "   ⚠️  oe-status layers directory not found"
    fi
    
    # Copy oe-status mapserver header
    if [ -f "$PROJECT_ROOT/docker/oe-status/mapserver/oe-status_reproject.header" ]; then
        cp "$PROJECT_ROOT/docker/oe-status/mapserver/oe-status_reproject.header" "$TARGET_CONFIG_DIR/config/mapserver/"
        echo "   ✅ Copied oe-status_reproject.header"
    else
        echo "   ⚠️  oe-status_reproject.header not found"
    fi
    
    # Create generic header files needed by oe-status endpoints
    # These are referenced by oe-status.yaml and oe-status_reproject.yaml
    for header_type in "header_gc" "header_gts" "header_twms_gc"; do
        generic_header="$TARGET_CONFIG_DIR/config/conf/${header_type}.xml"
        # Use epsg4326 as the base for generic headers
        source_header="$TARGET_CONFIG_DIR/config/conf/epsg4326_${header_type}.xml"
        
        if [ -f "$source_header" ] && [ ! -f "$generic_header" ]; then
            cp "$source_header" "$generic_header"
            echo "   ✅ Created generic ${header_type}.xml"
        elif [ ! -f "$source_header" ]; then
            echo "   ⚠️  Source ${header_type} not found for creating generic version"
        fi
    done
}

# Process each projection
for proj in "${PROJECTIONS_TO_SETUP[@]}"; do
    echo ""
    echo "🔧 Processing $proj..."
    
    create_endpoint_configs "$proj"
    create_variant_headers "$proj"
    copy_projection_configs "$proj"
    create_layer_structure "$proj"
done

# Always copy oe-status configurations (needed for WMS healthcheck)
echo ""
copy_oe_status_configs

echo ""
echo "=========================================="
echo "📋 Next Steps"
echo "=========================================="
echo ""
echo "1. 📂 Organize your MRF data structure:"
echo "   $MRF_ARCHIVE_DIR/"
for proj in "${PROJECTIONS_TO_SETUP[@]}"; do
    echo "   ├── $proj/"
    echo "   │   ├── {LAYER_NAME_1}/"
    echo "   │   │   └── {YEAR}/ (*.mrf, *.idx, *.pjg files)"
    echo "   │   └── {LAYER_NAME_2}/"
    echo "   │       └── {YEAR}/ (*.mrf, *.idx, *.pjg files)"
done
echo ""

echo "2. 📝 Layer configuration files:"
echo "   Layer configs have been copied from $SOURCE_CONFIG_DIR and updated for local paths:"
for proj in "${PROJECTIONS_TO_SETUP[@]}"; do
    echo "   • $TARGET_CONFIG_DIR/config/layers/$proj/{LAYER_NAME}.yaml"
done
echo ""
echo "   💡 Key updates made automatically:"
echo "      - data_file_uri: '/onearth/archive/{projection}'" 
echo "      - idx_path: /onearth/idx/{projection}"
echo "   💡 You may need to adjust:"
echo "      - bbox: (coordinate bounds for the projection)"
echo "      - size_x, size_y: (dimensions of your MRF data)"
echo "      - tilematrixset: (appropriate for the projection)"
echo ""

echo "3. 🚀 Run the setup:"
echo "   ./setup-onearth-local.sh"
echo ""

echo "4. 🧪 Test your endpoints:"
for proj in "${PROJECTIONS_TO_SETUP[@]}"; do
    echo "   # Test $proj:"
    echo "   curl 'http://localhost/wmts/${proj}/all/1.0.0/WMTSCapabilities.xml'"
    echo "   curl 'http://localhost/wmts/${proj}/best/1.0.0/WMTSCapabilities.xml'"
    echo "   curl 'http://localhost/wmts/${proj}/std/1.0.0/WMTSCapabilities.xml'"
    echo "   curl 'http://localhost/wmts/${proj}/nrt/1.0.0/WMTSCapabilities.xml'"
done
echo ""

echo "✨ Configuration generation complete!"
echo "   The script has created the directory structure and copied base configurations."
echo "   You'll still need to create the specific layer YAML files for your data." 