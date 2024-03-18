FROM varnish:7.4.2

COPY /docker/varnish_cache/default.vcl /etc/varnish/

USER root
RUN apt-get update && apt-get install -y vim && apt-get install -y curl

# Non-root user
RUN chmod 1777 /tmp && chown -hR www-data:www-data /etc/varnish/ && chown -hR www-data:www-data /var/log/varnish/ && chown -hR www-data:www-data /var/lib/varnish/

# Change user
USER www-data
