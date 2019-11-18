# OnEarth Deployment

This documentation will go through the steps needed to deploy OnEarth.

## Build and Run

To build the Docker images the OnEarth stack, execute:
`build.sh` from the source root.

To run all of the OnEarth Docker containers, execute:
`run.sh` from the source root.

## Container Startup Process

OnEarth container starts up and moves through the following steps:

### Read Endpoint Configurations

The configuration tool for each service deployed within a container is run for each endpoint (e.g. wmts/epsg4326/all). These configuration variables can be provided via command-line options, environment variables, or a YAML configuration. This configuration can remain mostly static and only needs to change when endpoint options need to be changed.

### Scrape Layer Configs and Set Up Layers
The configuration tool scrapes the layer config source path for this endpoint and sets up all the layers for all the requested services.
