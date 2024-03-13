# See https://www.varnish-software.com/developers/tutorials/example-vcl-template/ for more information

vcl 4.1;

import std;

backend server1 {
    .host = "172.17.0.1";
    .port = "8080";
    .max_connections = 100;
    .probe = {
	    .url = "/oe-status/Raster_Status/default/2004-08-01/16km/0/0/0.jpeg";
        .interval  = 1m;
        .timeout   = 90s;
        .window    = 5;
        .threshold = 3;
    }
    .connect_timeout        = 90s;
    .first_byte_timeout     = 90s;
    .between_bytes_timeout  = 30s;
}

acl purge {
    "localhost";
    "0.0.0.0";
    "::1";
}

sub vcl_recv {
    set req.http.Host = regsub(req.http.Host, ":[0-9]+", "");
    unset req.http.proxy;
    set req.url = std.querysort(req.url);
    set req.url = regsub(req.url, "\?$", "");
    set req.http.Surrogate-Capability = "key=ESI/1.0";

    if (std.healthy(req.backend_hint)) {
        set req.grace = 10s;
    }

    if (!req.http.X-Forwarded-Proto) {
        if(std.port(server.ip) == 443 || std.port(server.ip) == 8443) {
            set req.http.X-Forwarded-Proto = "https";
        } else {
            set req.http.X-Forwarded-Proto = "https";
        }
    }

    if (req.http.Upgrade ~ "(?i)websocket") {
        return (pipe);
    }

    if (req.url ~ "(\?|&)(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=") {
        set req.url = regsuball(req.url, "&(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=([A-z0-9_\-\.%25]+)", "");
        set req.url = regsuball(req.url, "\?(utm_source|utm_medium|utm_campaign|utm_content|gclid|cx|ie|cof|siteurl)=([A-z0-9_\-\.%25]+)", "?");
        set req.url = regsub(req.url, "\?&", "?");
        set req.url = regsub(req.url, "\?$", "");
    }

    if (req.method == "PURGE") {
        if (!client.ip ~ purge) {
            return (synth(405, client.ip + " is not allowed to send PURGE requests."));
        }
        return (purge);
    }

    if (req.method != "GET" &&
        req.method != "HEAD" &&
        req.method != "PUT" &&
        req.method != "POST" &&
        req.method != "TRACE" &&
        req.method != "OPTIONS" &&
        req.method != "PATCH" &&
        req.method != "DELETE") {
        return (pipe);
    }

    if (req.method != "GET" && req.method != "HEAD") {
        return (pass);
    }

    if (req.url ~ "^[^?]*\.(7z|avi|bmp|bz2|css|csv|doc|docx|eot|flac|flv|gif|gz|ico|jpeg|jpg|js|less|mka|mkv|mov|mp3|mp4|mpeg|mpg|odt|ogg|ogm|opus|otf|pdf|png|ppt|pptx|rar|rtf|svg|svgz|swf|tar|tbz|tgz|ttf|txt|txz|wav|webm|webp|woff|woff2|xls|xlsx|xml|xz|zip)(\?.*)?$") {
        unset req.http.Cookie;
        return(hash);
    }

    set req.http.Cookie = regsuball(req.http.Cookie, "(__utm|_ga|_opt)[a-z_]*=[^;]+(; )?", "");
    set req.http.Cookie = regsuball(req.http.Cookie, "(__)?hs[a-z_\-]+=[^;]+(; )?", "");
    set req.http.Cookie = regsuball(req.http.Cookie, "hubspotutk=[^;]+(; )?", "");
    set req.http.Cookie = regsuball(req.http.Cookie, "_hj[a-zA-Z]+=[^;]+(; )?", "");
    set req.http.Cookie = regsuball(req.http.Cookie, "(NID|DSID|__gads|GED_PLAYLIST_ACTIVITY|ACLK_DATA|ANID|AID|IDE|TAID|_gcl_[a-z]*|FLC|RUL|PAIDCONTENT|1P_JAR|Conversion|VISITOR_INFO1[a-z_]*)=[^;]+(; )?", "");
    set req.http.Cookie = regsuball(req.http.Cookie, "^;\s*", "");

    if (req.http.cookie ~ "^\s*$") {
        unset req.http.cookie;
    }
}

sub vcl_hash {
    hash_data(req.http.X-Forwarded-Proto);
}

sub vcl_backend_response {

	# GetCapabilities
    if (bereq.url ~ "^[^?]*\.xml") {
		unset beresp.http.Set-Cookie;
		# Keep the GetCapabiltiies documents in cache for 1 hour
        set beresp.ttl = 1h;
	}
    # Non-GC requests
	else if (bereq.url ~ "^[^?]*\.(7z|avi|bmp|bz2|css|csv|doc|docx|eot|flac|flv|gif|gz|ico|jpeg|jpg|js|less|mka|mkv|mov|mp3|mp4|mpeg|mpg|odt|ogg|ogm|opus|otf|pdf|png|ppt|pptx|rar|rtf|svg|svgz|swf|tar|tbz|tgz|ttf|txt|txz|wav|webm|webp|woff|woff2|xls|xlsx|xz|zip)(\?.*)?$") {
        unset beresp.http.Set-Cookie;
        set beresp.uncacheable = true;
        set beresp.ttl = 1d; 
    }

    if (beresp.http.Surrogate-Control ~ "ESI/1.0") {
        unset beresp.http.Surrogate-Control;
        set beresp.do_esi = true;
    }

	# Serve expired cache content for up to an additional 30 seconds while a new request to OnEarth is being performed
	set beresp.grace = 30s;
}