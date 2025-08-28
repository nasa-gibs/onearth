# Local OnEarth Deployment

This documentation describes how to deploy OnEarth locally using your own MRF (Meta Raster Format) data archive.

## Local Deployment Components

The local deployment system consists of the following components located in `docker/local-deployment/`:

- `setup-onearth-local.sh` - Main deployment script
- `generate-configs.sh` - Configuration generation script  
- `docker-compose.local.yml` - Docker Compose configuration
- `generate-data-directories.sh` - Generate Data Directories to place data 
- `templates/` - Configuration templates for endpoints and layers

### Data Directory Structure

The deployment uses configurable directory names within `docker/local-deployment/`:

- **MRF Archive Directory** (default: `docker/local-deployment/local-mrf-archive`): Contains MRF data organized by projection (supplied by the user)
- **Source Config Directory** (default: `docker/local-deployment/downloaded-onearth-configs`): Contains source layer configurations (supplied by the user)
- **Target Config Directory** (default: `docker/local-deployment/onearth-configs`): Generated local configurations
- **Shapefile Archive Directory (Optional)** (default: `docker/local-deployment/local-shp-archive`): Contains shapefile data organized by projection (supplied by the user)

```
docker/local-deployment/
├── local-mrf-archive/          # MRF data files
│   ├── epsg4326/
│   │   ├── LAYER_NAME/
│   │   │   └── YYYY/
│   │   │       ├── *.mrf
│   │   │       ├── *.idx
│   │   │       └── *.pjg
│   │   └── ...
│   └── ...
└── onearth-configs/            # Generated configurations
    └── config/
        ├── endpoint/
        ├── layers/
        ├── conf/
        └── mapserver/
```

## Deployment Process

**NOTE** You can create the folders to add your MRFs and configs to with `./generate-data-directories.sh`

### Step 1: Data Organization

Organize MRF files by projection within the MRF archive directory:

```
local-mrf-archive/
├── epsg4326/
│   └── LAYER_NAME/
│       └── 2024/
│           ├── LAYER_NAME-2024001000000.mrf
│           ├── LAYER_NAME-2024001000000.idx
│           └── LAYER_NAME-2024001000000.pjg
├── epsg3857/
└── ...
```

If you intend to serve vectors via WMS, organize shapefiles by projection within the shapefile archive directory. The corresponding layer MRF/IDX/PVT files should be in local-mrf-archive for the shapefiles to be viewed

```
local-shp-archive/
├── epsg4326/
│   └── LAYER_NAME/
│       └── 2024/
│           ├── LAYER_NAME-2024001000000.shp
│           ├── LAYER_NAME-2024001000000.dbf
│           ├── LAYER_NAME-2024001000000.prj
│           └── LAYER_NAME-2024001000000.shx
├── epsg3857/
└── ...
```

### Step 2: Source Configuration Preparation

If existing OnEarth layer configurations are available (e.g., from AWS deployment), place them in:

```
downloaded-onearth-configs/config/layers/PROJECTION/<all|best|nrt|std>/LAYER_NAME.yaml
```

Otherwise, you will need to manually create the layer configuration files and place them in the appropriate directories following Step 3. See [configuration.md](./configuration.md) for more information on creating layer configuration files.

### Step 3: Configuration Generation

Execute the configuration generation script:

```bash
# From docker/local-deployment/ directory
./generate-configs.sh [projections...]

# From project root
./docker/local-deployment/generate-configs.sh [projections...]
```

The script performs the following operations:
- Creates endpoint configurations for specified projections
- Copies layer configurations into their correct locations
- Generates required MapServer configuration files

#### Configuration Generation Options

```bash
# Generate configurations for specific projections
./generate-configs.sh epsg4326 epsg3857

# Use custom directory paths
./generate-configs.sh -s source-configs -t target-configs epsg4326

# Command line options
-s, --source-config DIR   Source config directory (default: downloaded-onearth-configs)
-t, --target-config DIR   Target config directory (default: onearth-configs)
-h, --help               Show help message
```

### Step 4: Service Deployment

Deploy OnEarth services using the setup script:

```bash
# From docker/local-deployment/ directory
./setup-onearth-local.sh [options]

# From project root
./docker/local-deployment/setup-onearth-local.sh [options]
```

#### Deployment Options

```bash
# Basic deployment (builds missing images only).
./setup-onearth-local.sh

# Force rebuild all images
./setup-onearth-local.sh --force-build-all

# Rebuild specific services
./setup-onearth-local.sh --service "tile-services capabilities"

# Use custom directories
./setup-onearth-local.sh -m custom-mrf-dir -p custom-shp-dir -c target-configs

# Use version-only tags (useful for pulling existing images from Docker Hub)
./setup-onearth-local.sh --version-only

# Complete environment teardown
./setup-onearth-local.sh --teardown
```

#### Updating Containers after Configuration or Code Changes

If you've only made changes to the configuration files, running `./setup-onearth-local.sh` will stop the existing containers and start up new containers that are configured using the latest versions of the configuration files.

If you've made code changes to any of the images, you will need to run `./setup-onearth-local.sh --force-build-all` or `./setup-onearth-local.sh --service "<service name(s)>"` so that new images are built with the latest code changes before the new containers start up.

*Note: the OpenLayers Demo Endpoints (such as at http://localhost/demo/wmts/epsg4326/) tend to be cached by the browser, so updates to layer configurations may not immediately appear without clearing your browser's cache.*

**Available command line options:**
- `-m, --mrf-archive DIR` - MRF archive directory
- `-p, --shp-archive DIR` - Shapefile archive directory
- `-c, --config DIR` - Configuration directory
- `-b, --build` - Force rebuild all Docker images
- `--build-deps` - Rebuild only base dependencies
- `-s, --service SERVICES` - Rebuild specified services (space-separated)
- `--no-build` - Start without building (requires existing images)
- `-v, --version-only` - Use version-only tags (e.g., 2.9.0 instead of 2.9.0-3)
- `--teardown` - Remove all OnEarth containers and networks
- `-h, --help` - Show help message

## Projection-Specific Configuration

### Automatic Configuration Updates

The configuration generation script automatically updates layer configurations with:
- `data_file_uri: '/onearth/mrf-archive/{projection}'`
- `data_file_uri: '/onearth/shp-archive/{projection}'`
- `idx_path: /onearth/idx/{projection}`

## Deployed Services

The local deployment creates the following Docker services:

- **onearth-demo** (port 80) - Interactive demo page with endpoint testing
- **onearth-capabilities** (port 8081) - WMTS GetCapabilities and metadata services
- **onearth-tile-services** (port 443) - WMTS tile serving
- **onearth-time-service** (port 6379) - Time dimension support
- **onearth-reproject** (port 8082) - On-the-fly reprojection service
- **onearth-wms** (port 8443) - WMS service

### Volume Mounts

Docker containers mount the following volumes:
- MRF archive directory → `/onearth/mrf-archive` (read-only)
- Shapefile archive directory → `/onearth/shp-archive` (read-only)
- Configuration directory → `/etc/onearth/config` (read-only)

## Testing Deployment

### Service Verification

Test deployed services using the following endpoints:

```bash
# WMTS GetCapabilities
curl 'http://localhost/wmts/{PROJECTION}/1.0.0/WMTSCapabilities.xml'

# WMTS tile request
curl 'http://localhost/wmts/{PROJECTION}/1.0.0/{LAYER_ID}/default/{TIME}/{TILEMATRIXSET}/{Z}/{Y}/{X}.jpg'

# WMS GetCapabilities
curl 'http://localhost/wms/{PROJECTION}?SERVICE=WMS&REQUEST=GetCapabilities'

# Interactive demo page
http://localhost/demo/
```

## Troubleshooting

### Complete Environment Reset

For persistent issues, perform a complete environment reset:

```bash
# Remove all OnEarth containers and networks
./setup-onearth-local.sh --teardown

# Rebuild and restart
./setup-onearth-local.sh --build
```

### Common Issues

**No tiles loading:**
- Verify MRF files exist in expected directory structure
- Check `data_file_uri` paths in layer configurations
- Ensure `size_x`, `size_y` match MRF data dimensions

**Empty GetCapabilities responses:**
- Verify layer YAML files exist in `config/layers/PROJECTION/`
- Check endpoint configurations in `config/endpoint/`
- Review OnEarth config logs: `docker exec onearth-capabilities cat /var/log/onearth/config.log`
- Check Apache error logs: `docker exec onearth-capabilities cat /var/log/httpd/error_log`

**Time dimension issues:**
- Verify `time_config` settings in layer YAML files
- Check MRF file naming patterns
- Ensure `year_dir: true` for year-based directory structures

### Configuration Validation

```bash
# Verify MRF files
find local-mrf-archive -name "*.mrf"

# Check layer configurations
find onearth-configs/config/layers -name "*.yaml"

# Validate YAML syntax
yamllint onearth-configs/config/layers/PROJECTION/*.yaml
```

### Log Analysis

For detailed troubleshooting, examine the following log files:

- **OnEarth Configuration Logs**: `docker exec onearth-capabilities cat /var/log/onearth/config.log`
  - Shows configuration parsing and loading issues
  - Displays endpoint and layer discovery results

- **Apache Error Logs**: `docker exec onearth-capabilities cat /var/log/httpd/error_log`
  - Shows HTTP request errors and server issues
  - Displays Apache module errors

- **WMS MapServer Logs**: `docker exec onearth-wms cat /var/log/mapserver/error.log`
  - Shows MapServer issues
  - Only available in the WMS container

- **Demo Container Logs**: `docker exec onearth-demo cat /var/log/httpd/error_log`
  - Shows demo page generation and serving issues

## Script Execution Context

Both `setup-onearth-local.sh` and `generate-configs.sh` can be executed from either the `docker/local-deployment/` directory or the project root. The scripts automatically detect their execution context and adjust paths accordingly.