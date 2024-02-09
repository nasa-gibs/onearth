ARG ONEARTH_VERSION
FROM nasagibs/onearth-deps:ONEARTH_VERSION
FROM varnish

COPY /docker/varnish_cache/default.vcl /etc/varnish/

USER root
RUN apt-get update && apt-get install -y vim && apt-get install -y curl
