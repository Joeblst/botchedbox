FROM httpd:2.4.62

RUN apt-get update && apt-get install -y \
    apache2 \
    apache2-utils \
    libapache2-mod-security2 \
    libapache2-mod-evasive \
    ssl-cert \
    && rm -rf /var/lib/apt/lists/*

RUN a2enmod \
    rewrite \
    headers \
    ssl \
    proxy \
    proxy_http \
    proxy_balancer \
    lbmethod_byrequests \
    lbmethod_bytraffic \
    lbmethod_bybusyness \
    deflate \
    expires \
    include \
    setenvif \
    status \
    info \
    auth_basic \
    auth_digest \
    authn_file \
    authz_groupfile \
    authz_user \
    authz_host \
    authz_core \
    access_compat \
    autoindex \
    dir \
    mime \
    negotiation \
    filter \
    security2 \
    evasive \
    ratelimit

EXPOSE 80

CMD ["httpd-foreground"]
