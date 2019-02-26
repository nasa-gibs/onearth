#!/usr/bin/env python

import os
import sys

test_urls = sys.argv[1]

print "Using input file " + test_urls

with open(test_urls) as f:
    urls = f.readlines()
 
#idx_files = len(urls)/10000 

for idx in range(0, 10):
    file = open(test_urls+"_"+str(idx),"w")
    start = idx * 10000
    i = 0
    while i <= len(urls):
        url_i = i+start
        if url_i >= len(urls):
            url_i = url_i - len(urls)
        file.write(urls[url_i])
        i+=1
        if i == 10000:
            file.close()
            print "Wrote " + test_urls+"_"+str(idx)
            break   