FROM almalinux:9.2
FROM varnish

COPY /docker/varnish_cache/default.vcl /etc/varnish/

USER root
RUN apt-get update && apt-get install -y vim && apt-get install -y curl
