FROM varnish:7.5.0-alpine

COPY /docker/varnish_cache/default.vcl /etc/varnish/

USER root

# Add vim & curl for debugging purposes
RUN apk update && apk add vim && apk add curl

# Non-root user
RUN set -x ; \
  addgroup -g 82 -S www-data ; \
  adduser -u 82 -D -S -G www-data www-data
RUN chmod 1777 /tmp && chown -hR www-data:www-data /etc/varnish/ && chown -hR www-data:www-data /var/log/varnish/ && chown -hR www-data:www-data /var/lib/varnish/

# Change user
USER www-data
