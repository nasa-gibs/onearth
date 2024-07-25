# mod_brunsli

An Apache HTTPD brunsli - JPEG convertor output filter

[Brunsli][] is a fast lossless JPEG recompressor that is included in the
[committee draft of the JPEG XL standard][CD]. This Apache HTTPD module allows serving legacy JFIF JPEG from 
recompressed Brunsli files, saving about 20% of the JPEG storage space by using the DBRUNSLI filter. 
The reverse conversion is also possible, generating brunsli files from JFIF JPEGs.

[Brunsli]: https://github.com/google/brunsli
[CD]: https://arxiv.org/abs/1908.03565

As an Apache HTTPD output filter named "DBRUNSLI", it can be enabled using 
[SetOutputFilter directive](http://httpd.apache.org/docs/current/mod/core.html#setoutputfilter) or 
using [mod_filter](https://httpd.apache.org/docs/2.4/mod/mod_filter.html).  
When enabled, DBRUNSLI filter activates when it detects brunsli content, converts it back to the original 
JPEG and sends that JPEG to the user.
A second filter named "CBRUNSLI" is available, generating brunsli formatted output from a JFIF input. 
The mime type used for brunsli formatted output is `image/x-j`.

Currently these filters have a hardcoded input size limit of 1MB, if the input is larger it will be forwarded 
without conversion.
The input and the output will both be fully present in RAM at the end of the decoding, a busy server memory 
footprint might be significant. CPU utilization and request latency increase are low, with the brunsli encoding 
being slower than the decoding.
