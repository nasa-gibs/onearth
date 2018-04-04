#!/usr/bin/python

import sys, string, os, getopt
import json
import re
import traceback
import numpy as np


class uuidDetails():
   def __init__(self, uuid):
       self.uuid            = uuid
       self.begin_timestamp = None
       self.end_timestamp   = None
       self.s3_read_dur     = None
       self.idx_read_dur    = None

   def __str__(self):
      return self.uuid + ": " + \
         str(self.begin_timestamp) + " / " + \
         str(self.end_timestamp) + " / " + \
         str(self.s3_read_dur) + " / " + \
         str(self.idx_read_dur)

def usage():
   print ("analyze-event-log.py [OPTIONS]")
   print ("  -e/--events_log    : Path to log file with CloudWatch events")
   print ("  -v/--verbose      : Verbose Output (Optional)")


eventsLog = None
verbose   = False

try:
   opts, args = getopt.getopt(sys.argv[1:],"he:v",["events_log","verbose"])
except getopt.GetoptError:
   usage()
   sys.exit(2)

for opt, arg in opts:
   if opt == '-h':
      usage()
      sys.exit()
   elif opt in ("-e", "--events_log"):
      eventsLog = arg
   elif opt in ("-v", "--verbose"):
      verbose = True  
      
# Open the product configuration file
if not eventsLog:
   print("Events Log must be provided.")
   sys.exit(-1)

try:
   eventsData = json.load(open(eventsLog))['events']
except:
   print("Error parsing events log.\n" + traceback.format_exc())
   sys.exit(-1)

eventDetailsDict   = {}
getEventKByteItems = []

matchBegin = re.compile(".*begin_onearth_handle.*")
matchEnd   = re.compile(".*end_mod_mrf_handle.*")
matchS3    = re.compile(".*mod_mrf_s3_read.*")
matchIdx   = re.compile(".*mod_mrf_index_read.*")
matchGet   = re.compile(".*GET .mrf_endpoint.*")


# Parse event data into uuidDetails() objects
for event in eventsData:

   try :
      if matchBegin.search(event["message"]):
         m = re.match(".*timestamp=([0-9]*), uuid=(.*)", event["message"])
         if not m or len(m.groups()) != 2:
            print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
         else:
            if m.group(2) not in eventDetailsDict:
               eventDetailsDict[m.group(2)] = uuidDetails(m.group(2))
               
            eventDetailsDict[m.group(2)].begin_timestamp = float(m.group(1)) / 1000

      elif matchEnd.search(event["message"]):
         m = re.match(".*timestamp=([0-9]*), uuid=(.*)", event["message"])
         if not m or len(m.groups()) != 2:
            print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
         else:
            if m.group(2) not in eventDetailsDict:
               eventDetailsDict[m.group(2)] = uuidDetails(m.group(2))
               
            eventDetailsDict[m.group(2)].end_timestamp = float(m.group(1)) / 1000

      elif matchS3.search(event["message"]):
         m = re.match(".*duration=([0-9]*), uuid=(.*)", event["message"])
         if not m or len(m.groups()) != 2:
            print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
         else:
            if m.group(2) not in eventDetailsDict:
               eventDetailsDict[m.group(2)] = uuidDetails(m.group(2))
               
            eventDetailsDict[m.group(2)].s3_read_dur = float(m.group(1)) / 1000

      elif matchIdx.search(event["message"]):
         m = re.match(".*duration=([0-9]*), uuid=(.*)", event["message"])
         if not m or len(m.groups()) != 2:
            print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
         else:
            if m.group(2) not in eventDetailsDict:
               eventDetailsDict[m.group(2)] = uuidDetails(m.group(2))
            
            eventDetailsDict[m.group(2)].idx_read_dur = float(m.group(1)) / 1000

      elif matchGet.search(event["message"]):
         m = re.match(".*GET .*200 ([0-9]*) .*", event["message"])
         if not m or len(m.groups()) != 1:
            print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
         else:
            getEventKByteItems.append(float(m.group(1)) / 1000)

      else:
         if verbose: print("Unknown log message: (" + str(event["timestamp"]) + "): " + event["message"])
   except:
      print("Error parsing message: (" + str(event["timestamp"]) + "): " + event["message"] + "\n" + traceback.format_exc())


# Look for invalid uuidDetails()
badUuids = []

for details in eventDetailsDict.values():
   
   valid = (details.begin_timestamp and details.end_timestamp and details.s3_read_dur and details.idx_read_dur) and \
           (details.end_timestamp - details.begin_timestamp > 0)
   
   if not valid:
      if verbose: print("Invalid uuid details: " + str(details))
      
      badUuids.append(details.uuid)

for uuid in badUuids:
   del(eventDetailsDict[uuid])


# Build arrays for analysis
durReadItems = []
s3ReadItems  = []
idxReadItems = []

for details in eventDetailsDict.values():
   durReadItems.append(details.end_timestamp - details.begin_timestamp)
   s3ReadItems.append(details.s3_read_dur)
   idxReadItems.append(details.idx_read_dur)


# Calculate and print statistics
durReadArr = np.array(durReadItems)

print("onearth-mod_mrf")
print("\tcount:           " + str(len(durReadItems)))
print("\tmean:            " + str(round(np.mean(durReadArr),2)) + " ms")
print("\tmax:             " + str(round(np.amax(durReadArr),2)) + " ms")
print("\tmin:             " + str(round(np.amin(durReadArr),2)) + " ms")
print("\t25th percentile: " + str(round(np.percentile(durReadArr, 25),2)) + " ms")
print("\t50th percentile: " + str(round(np.percentile(durReadArr, 50),2)) + " ms")
print("\t75th percentile: " + str(round(np.percentile(durReadArr, 75),2)) + " ms")
print("\t95th percentile: " + str(round(np.percentile(durReadArr, 95),2)) + " ms")
print("\t98th percentile: " + str(round(np.percentile(durReadArr, 98),2)) + " ms")
print("\t99th percentile: " + str(round(np.percentile(durReadArr, 99),2)) + " ms")


s3ReadArr = np.array(s3ReadItems)

print("mod_mrf_s3_read")
print("\tcount:           " + str(len(s3ReadItems)))
print("\tmean:            " + str(round(np.mean(s3ReadArr),2)) + " ms")
print("\tmax:             " + str(round(np.amax(s3ReadArr),2)) + " ms")
print("\tmin:             " + str(round(np.amin(s3ReadArr),2)) + " ms")
print("\t25th percentile: " + str(round(np.percentile(s3ReadArr, 25),2)) + " ms")
print("\t50th percentile: " + str(round(np.percentile(s3ReadArr, 50),2)) + " ms")
print("\t75th percentile: " + str(round(np.percentile(s3ReadArr, 75),2)) + " ms")
print("\t95th percentile: " + str(round(np.percentile(s3ReadArr, 95),2)) + " ms")
print("\t98th percentile: " + str(round(np.percentile(s3ReadArr, 98),2)) + " ms")
print("\t99th percentile: " + str(round(np.percentile(s3ReadArr, 99),2)) + " ms")


idxReadArr = np.array(idxReadItems)

print("mod_mrf_index_read")
print("\tcount:           " + str(len(idxReadItems)))
print("\tmean:            " + str(round(np.mean(idxReadArr),2)) + " ms")
print("\tmax:             " + str(round(np.amax(idxReadArr))) + " ms")
print("\tmin:             " + str(round(np.amin(idxReadArr))) + " ms")
print("\t25th percentile: " + str(round(np.percentile(idxReadArr, 25),2)) + " ms")
print("\t50th percentile: " + str(round(np.percentile(idxReadArr, 50),2)) + " ms")
print("\t75th percentile: " + str(round(np.percentile(idxReadArr, 75),2)) + " ms")
print("\t95th percentile: " + str(round(np.percentile(idxReadArr, 95),2)) + " ms")
print("\t98th percentile: " + str(round(np.percentile(idxReadArr, 98),2)) + " ms")
print("\t99th percentile: " + str(round(np.percentile(idxReadArr, 99),2)) + " ms")


getKBytesArr = np.array(getEventKByteItems)

print("apache_get_bytes")
print("\tcount:           " + str(len(getEventKByteItems)))
print("\tmean:            " + str(round(np.mean(getKBytesArr),2)) + " kb")
print("\tmax:             " + str(round(np.amax(getKBytesArr))) + " kb")
print("\tmin:             " + str(round(np.amin(getKBytesArr))) + " kb")
print("\t25th percentile: " + str(round(np.percentile(getKBytesArr, 25),2)) + " kb")
print("\t50th percentile: " + str(round(np.percentile(getKBytesArr, 50),2)) + " kb")
print("\t75th percentile: " + str(round(np.percentile(getKBytesArr, 75),2)) + " kb")
print("\t95th percentile: " + str(round(np.percentile(getKBytesArr, 95),2)) + " kb")
print("\t98th percentile: " + str(round(np.percentile(getKBytesArr, 98),2)) + " kb")
print("\t99th percentile: " + str(round(np.percentile(getKBytesArr, 99),2)) + " kb")
