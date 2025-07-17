# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

OnEarth is a high-performance web service platform for efficiently serving georeferenced raster imagery and vectors at multiple spatial resolutions. It powers visualization tools like NASA Worldview and is actively maintained by the NASA Global Imagery Browse Services (GIBS) Project.

## Architecture

OnEarth is built on the **AHTSE (Apache HTTPD Tile Server Ecosystem)** framework, deploying as a microservices architecture with specialized Docker containers for different functions:

- **onearth-tile-services**: WMTS/TWMS tile serving using mod_mrf and mod_wmts_wrapper
- **onearth-time-service**: Time dimension handling with Redis backend
- **onearth-capabilities**: GetCapabilities document generation via Lua scripts
- **onearth-reproject**: Projection transformation services  
- **onearth-wms**: Traditional WMS services via MapServer
- **onearth-demo**: Demo interface and examples

### Key Components

**Apache Modules (src/modules/):**
- `mod_mrf`: Primary tile server serving from MRF (Meta Raster Format) files with high-performance tile delivery
- `mod_wmts_wrapper`: Converts WMTS requests to REST format, handles time dimensions
- `mod_reproject`: Handles projection changes and tile grid transformations
- `mod_twms`: Converts Tiled WMS requests to AHTSE REST format
- `mod_ahtse_png`: Real-time PNG chunk manipulation for dynamic colormap application and transparency support
- `mod_sfim`: Static file serving based on URL pattern matching for protocol handshake files
- `mod_ahtse_lua`: Lua script execution engine enabling dynamic content generation for services
- Additional transformation modules: mod_convert, mod_retile, mod_receive, mod_brunsli

**Services:**
- **GetCapabilities Service (gc_service)**: Lua-based service generating WMTS/TWMS GetCapabilities XML from YAML configs
- **Time Service**: Lua service for querying time periods and date snapping using Redis
- **WMS Service**: MapServer integration for traditional WMS capabilities

**Data Tools:**
- `mrfgen`: MRF file generation from various input formats
- `vectorgen`: Vector tile generation (MVT-MRF) from shapefiles/GeoJSON
- `colormaps`: Color palette management and conversion tools
- Various utility scripts in `src/scripts/`

## Build and Development

### Building Docker Images
```bash
# Build all OnEarth containers
./build.sh

# Run the complete OnEarth stack
./run.sh [USE_SSL] [SERVER_NAME]
```

### Testing
```bash
# Run tests in Docker (recommended)
./ci/run_test_in_docker.sh nasagibs/onearth-test:latest <test_file.py>

# Install test dependencies locally
pip3 install -r requirements.txt

# Run individual test
python3 src/test/test_<module>.py
```

### Build CI Test Image
```bash
./ci/build_test_image.sh <tag_name>
```

## Key File Locations

- **Configuration Templates**: `docker/sample_configs/`
- **Test Data**: `src/test/` (extensive test suites for all modules)
- **Documentation**: `doc/` (configuration, deployment, storage guides)
- **Module Source**: `src/modules/*/src/` (C++ Apache modules with Makefiles)
- **Python Tools**: `src/mrfgen/`, `src/vectorgen/`, `src/scripts/`

## Configuration System

OnEarth uses YAML-based configuration:
- **Endpoint configs**: Define WMTS/WMS service endpoints and projections
- **Layer configs**: Define individual layer properties, data sources, and temporal settings
- **Supports multiple projections**: EPSG:4326, EPSG:3857, EPSG:3031, EPSG:3413

Configuration files are organized hierarchically by projection and quality level (STD/NRT/Best).

## Data Formats

**Meta Raster Format (MRF)**: OnEarth's primary optimized format consisting of:
- Header file (.mrf): Metadata and structure
- Index file (.idx): Tile location lookup table  
- Data file (.ppg/.pjg/.ptf/.pvt/.lerc): Actual tile data

**Supported Formats**: JPEG, PNG, LERC, MVT for vectors, with compression options like ZENJPEG and Brunsli.

## Development Workflows

**Adding New Functionality:**
1. Identify the appropriate module/service (tile serving, time handling, capabilities generation)
2. For Apache modules: Work in `src/modules/*/src/` with C++
3. For services: Work with Lua scripts in respective service directories
4. For tools: Work with Python in `src/mrfgen/`, `src/vectorgen/`, etc.

**Testing Changes:**
1. Use Docker-based testing via `ci/run_test_in_docker.sh`
2. Comprehensive test suites cover all major functionality
3. Tests include both unit tests and integration tests with sample data

**Common Development Patterns:**
- Apache modules follow AHTSE patterns for request handling
- Configuration uses YAML format throughout
- Time handling leverages Redis for performance
- All components designed for horizontal scaling in cloud environments