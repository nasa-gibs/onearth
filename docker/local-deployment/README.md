# OnEarth Local Deployment

This directory contains scripts and configuration files for deploying OnEarth locally with your own MRF data.

## Quick Start

```bash
# Generate configurations for your projections
./generate-configs.sh epsg4326 epsg3857

# Deploy OnEarth services
./setup-onearth-local.sh

# Complete cleanup when done
./setup-onearth-local.sh --teardown
```

Scripts can be run from either this directory or from the project root.

## Documentation

For complete setup instructions, configuration options, and troubleshooting guidance, see:

**[doc/local_deployment.md](../../doc/local_deployment.md)**

## Directory Contents

- `setup-onearth-local.sh` - Main deployment script
- `generate-configs.sh` - Configuration generation script
- `docker-compose.local.yml` - Docker Compose configuration
- `templates/` - Configuration templates
- `local-mrf-archive/` - Your MRF data (create this)
- `local-shp-archive/` - Your shapefile data (create this if you want to serve vectors via WMS)
- `onearth-configs/` - Generated configurations (created by scripts)