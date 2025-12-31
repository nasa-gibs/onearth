# OnEarth Deployment

This documentation will go through the steps needed to deploy OnEarth.

## Build and Run

To build the Docker images the OnEarth stack, execute:
`build.sh` from the source root.

To run all of the OnEarth Docker containers, execute:
`run.sh` from the source root. If SSL is desired for production environments, execute: `run.sh "true" $SERVER_NAME`

### SSL/TLS Certs

OnEarth will use SSL/TLS certs files in the current directory `./certs/` folder upon startup. This folder should contain three files that must be kept securely (AWS Secrets Manager is recommended):
- onearth.crt - The SSL certificate
- onearth.key - The encrypted private key
- onearth.pass - A passphrase for decrypting the private key

These files may be obtained by requesting through AWS Certificate Manager or another trusted certificate manager and then exporting. The domain name should match the public endpoint. If the `./certs/` directory doesn't exist, it must be created and the files copied into it.

If the `USE_SSL` environment variable is set to `true`, the files will be copied to Docker containers that have external access (onearth-tile-services and onearth-wms) into the `/etc/pki/tls/private/` directory and used by Apache HTTPD to enable end-to-end https access.


## Container Startup Process

OnEarth container starts up and moves through the following steps:

### Read Endpoint Configurations

The configuration tool for each service deployed within a container is run for each endpoint (e.g. wmts/epsg4326/all). These configuration variables can be provided via command-line options, environment variables, or a YAML configuration. This configuration can remain mostly static and only needs to change when endpoint options need to be changed.

### Scrape Layer Configs and Set Up Layers
The configuration tool scrapes the layer config source path for this endpoint and sets up all the layers for all the requested services.

### Making and deploying changes to a module after setup
1. `docker exec -it` into the container of the module you would like to modify. Can determine this based on what Dockerfile installs the module 
2. Modify the file in `/home/oe2/onearth/src/modules/`
3. Rebuild the module. The best way to do this is copy the way the Dockerfile initially builds the module. Might have to reinstall packages like luarocks 
5. `rm -rf /etc/httpd/conf.d/cache.conf` option for the capabilities container to disable GetCapabilities server side caching
6. Restart Apache with `httpd -k restart`
7. Run the start script in `cd /home/oe2/onearth/docker/` for the container you are in with the correct arguments 