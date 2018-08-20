#!/usr/bin/python

import sys, string, os, getopt
import json
import re
import traceback
import numpy as np


logMetrics = [
               ["begin_onearth_handle","timestamp", True],
               ["end_onearth_handle","timestamp", True],
               ["begin_mod_mrf_handle","timestamp", True],
               ["end_mod_mrf_handle","timestamp", True],
               ["mod_mrf_index_read","duration", True],
               ["mod_mrf_s3_read","duration", True],
               ["begin_send_to_date_service","timestamp", False],
               ["end_send_to_date_service","timestamp", False],
               ["begin_mod_reproject_handle","timestamp", False],
               ["end_mod_reproject_handle","timestamp", False]
             ]

class uuidDetails():
   def __init__(self, uuid):
       self.uuid            = uuid

#   def __str__(self):
#      return self.uuid + ": " + \
#         str(self.begin_timestamp) + " / " + \
#         str(self.end_timestamp) + " / " + \
#         str(self.s3_read_dur) + " / " + \
#         str(self.idx_read_dur)

def usage():
   print ("analyze-event-log.py [OPTIONS]")
   print ("  -e/--events_log    : Path to log file with CloudWatch events")
   print ("  -v/--verbose      : Verbose Output (Optional)")


def calculateAndPrintStats(metric, values):
   npArray = np.array(values)
   
   print(metric)
   print("\tcount:           " + str(len(values)))
   print("\tmean:            " + str(round(np.mean(npArray),2)) + " ms")
   print("\tmax:             " + str(round(np.amax(npArray),2)) + " ms")
   print("\tmin:             " + str(round(np.amin(npArray),2)) + " ms")
   print("\t25th percentile: " + str(round(np.percentile(npArray, 25),2)) + " ms")
   print("\t50th percentile: " + str(round(np.percentile(npArray, 50),2)) + " ms")
   print("\t75th percentile: " + str(round(np.percentile(npArray, 75),2)) + " ms")
   print("\t95th percentile: " + str(round(np.percentile(npArray, 95),2)) + " ms")
   print("\t98th percentile: " + str(round(np.percentile(npArray, 98),2)) + " ms")
   print("\t99th percentile: " + str(round(np.percentile(npArray, 99),2)) + " ms")



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
metricMatchers     = {}

for metric in logMetrics:
   messageMatcher = re.compile(".*" + metric[0] + ".*")
   messageParser  = re.compile((".*timestamp=([0-9]*)" if metric[1] == "timestamp" 
                                 else ".*duration=([0-9]*)") + ", uuid=(.*)")
   metricMatchers[metric[0]] = [messageMatcher, messageParser]


#matchGet   = re.compile(".*GET .mrf_endpoint.*")


# Parse event data into uuidDetails() objects
for event in eventsData:

   try :
      for metric in metricMatchers:
         matched = False
         
         if metricMatchers[metric][0].search(event["message"]):
            matched = True
            
            m = metricMatchers[metric][1].match(event["message"])
            if not m or len(m.groups()) != 2:
               print("Bogus log message: (" + str(event["timestamp"]) + "): " + event["message"])
            else:
               if m.group(2) not in eventDetailsDict:
                  eventDetailsDict[m.group(2)] = uuidDetails(m.group(2))
               
               setattr(eventDetailsDict[m.group(2)], metric, float(m.group(1)) / 1000)
            
            break

      if not matched:
         if verbose: print("Unknown log message: (" + str(event["timestamp"]) + "): " + event["message"])
   except:
      print("Error parsing message: (" + str(event["timestamp"]) + "): " + event["message"] + "\n" + traceback.format_exc())


# Look for invalid uuidDetails()
badUuids = []

for details in eventDetailsDict.values():
   valid = True
   
   for metric in logMetrics:
      if metric[1] == "duration":
         # If required and missing...
         if metric[2] and metric[0] not in dir(details):
            valid = False
            if verbose: print("Missing metric (" + metric[0] + ") : " + details.uuid)
         
      elif metric[1] == "timestamp" and metric[0].startswith("begin"):
         # If required and 'begin' is missing...
         if metric[2] and metric[0] not in dir(details):
            valid = False
            if verbose: print("Missing metric (" + metric[0] + ") : " + details.uuid)

         #Elif the 'begin' was found, but 'end' was not
         elif metric[0] in dir(details) and metric[0].replace("begin","end") not in dir(details):
            valid = False
            if verbose: print("Missing metric (" + metric[0].replace("begin","end") + ") : " + details.uuid)

         #Elif 
         elif dir(details) and metric[0].replace("begin","end") in dir(details) and \
               getattr(details, metric[0].replace("begin","end"),-1) - getattr(details, metric[0],-1) < 0:
            if verbose: print("Invalid begin/end metric (" + metric[0].replace("begin_","") + ") : " + details.uuid)
            
   if not valid:
      badUuids.append(details.uuid)

for uuid in badUuids:
   del(eventDetailsDict[uuid])

# Calculate and Print Metrics
for metric in logMetrics:
   metricValues = []

   if metric[1] == "duration":
      for details in eventDetailsDict.values():
         if metric[0] in dir(details):
            metricValues.append(getattr(details, metric[0]))
   
   elif metric[1] == "timestamp" and metric[0].startswith("begin"):
      for details in eventDetailsDict.values():
         if metric[0] in dir(details):
            if getattr(details, metric[0].replace("begin","end")) - getattr(details, metric[0]) > 0:
                metricValues.append(getattr(details, metric[0].replace("begin","end")) - getattr(details, metric[0]))
         
   else:
      continue
   
   if len(metricValues) > 0:
      calculateAndPrintStats(metric[0], metricValues)

