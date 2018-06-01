#!/bin/env python

import os
import sys
import random
from datetime import date, timedelta, datetime

test_urls = sys.argv[1]
test_d1 = sys.argv[2]
test_d2 = sys.argv[3]

print "Using input file " + test_urls
print "Using starting date " + test_d1
print "Using ending date " + test_d2

with open(test_urls) as f:
    urls = f.readlines()
 
#d1 = date(2018, 1, 1)
#d2 = date(2018, 4, 10)
d1 = datetime.strptime(test_d1, '%Y-%m-%d')
d2 = datetime.strptime(test_d2, '%Y-%m-%d')

delta = d2 - d1
dates = []
for i in range(delta.days + 1):
    dates.append(d1 + timedelta(days=i))
print dates


for idx in range(0, 10):
    file = open(test_urls+"_"+str(idx),"w")
    start = idx * 10000
    i = 0
    while i <= len(urls):
        url_i = i+start
        if url_i >= len(urls):
            url_i = url_i - len(urls)
        new_url = urls[url_i].replace("DATE",random.SystemRandom().choice(dates).strftime("%Y-%m-%d"))
        file.write(new_url)
        i+=1
        if i == 10000:
            file.close()
            print "Wrote " + test_urls+"_"+str(idx)
            break   
