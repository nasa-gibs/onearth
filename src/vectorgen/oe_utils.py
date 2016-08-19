#!/bin/env python

# Copyright (c) 2002-2016, California Institute of Technology.
# All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
#      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
#      endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file contains various utilities for the OnEarth tools.
"""

import glob
import logging
import os
import subprocess
import sys
import time
import datetime
import socket
import urllib
import urllib2

basename = None

def sigevent(type, mssg, sigevent_url):
    """
    Send a message to sigevent service.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
                        'http://localhost:8100/sigevent/events/create'
    """
    # Constrain mssg to 256 characters (including '...').
    if len(mssg) > 256:
        mssg=str().join([mssg[0:253], '...'])
    print str().join(['sigevent ', type, ' - ', mssg])
    # Remove any trailing slash from URL.
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any question mark from URL.  It is added later.
    if sigevent_url[-1] == '?':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Remove any trailing slash from URL.  (Again.)
    if sigevent_url[-1] == '/':
        sigevent_url=sigevent_url[0:len(sigevent_url)-1]
    # Define sigevent parameters that get encoded into the URL.
    data={}
    data['type']=type
    data['description']=mssg
    data['computer']=socket.gethostname()
    data['source']='ONEARTH'
    data['format']='TEXT'
    data['category']='MRFGEN'
    data['provider']='GIBS'
    if basename != None:
        data['data']=basename
    # Format sigevent parameters that get encoded into the URL.
    values=urllib.urlencode(data)
    # Create complete URL.
    full_url=sigevent_url+'?'+values
    data=urllib2.urlopen(full_url)

def log_info_mssg(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print mssg
    logging.info(mssg)

def log_info_mssg_with_timestamp(mssg):
    """
    For information messages only.  Not for warning or error.
    Arguments:
        mssg -- 'message for operations'
    """
    # Send to log.
    print time.asctime()
    logging.info(time.asctime())
    log_info_mssg(mssg)

def log_sig_warn(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(time.asctime())
    logging.warning(mssg)
    # Send to sigevent.
    try:
        sent=sigevent('WARN', mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'
        
def log_sig_err(mssg, sigevent_url):
    """
    Send an error to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(time.asctime())
    logging.warning(mssg)
    # Send to sigevent.
    try:
        sent=sigevent('ERROR', mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'

def log_sig_exit(type, mssg, sigevent_url):
    """
    Send a message to the log, to sigevent, and then exit.
    Arguments:
        type -- 'INFO', 'WARN', 'ERROR'
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    exit_code = 0
    # Add "Exiting" to mssg.
    mssg=str().join([mssg, '  Exiting mrfgen.'])
    # Send to sigevent.
    try:
        sent=sigevent(type, mssg, sigevent_url)
    except urllib2.URLError:
        print 'sigevent service is unavailable'
    # Send to log.
    if type == 'INFO':
        log_info_mssg_with_timestamp(mssg)
    elif type == 'WARN':
        logging.warning(time.asctime())
        logging.warning(mssg)
    elif type == 'ERROR':
        logging.error(time.asctime())
        logging.error(mssg)
        exit_code = 1
    # Exit.
    sys.exit(exit_code)

def log_the_command(command_list):
    """
    Send a command list to the log.
    Arguments:
        command_list -- list containing all elements of a subprocess command.
    """
    # Add a blank space between each element.
    spaced_command=''
    for ndx in range(len(command_list)):
        spaced_command=str().join([spaced_command, command_list[ndx], ' '])
    # Send to log.
    log_info_mssg_with_timestamp(spaced_command)

def get_modification_time(filename):
    """
    Return (fake) floating point value of posix modification time for a file.
    The (fake) floating point value is yyyymmdd.hhmmss which may be treated 
    as a floating point number for the sake of time ordering.
    Arguments:
        filename -- name of file for which to return the modificaton time
    """
    # Get posix system time for mrf file to check the modification time.
    stats=os.stat(filename)
    # Convert st_mtime to time string "yyyymmdd.hhmmss".
    addt=time.strftime('%Y%m%d.%H%M%S', time.localtime(stats.st_mtime))
    mssg=str().join(['modification time ', addt, ' ', filename])
    # Send to log.
    log_info_mssg(mssg)
    # Return time as string.
    return addt

def get_dom_tag_value(dom, tag_name):
    """
    Return value of a tag from dom (XML file).
    Arguments:
        tag_name -- name of dom tag for which the value should be returned.
    """
    tag=dom.getElementsByTagName(tag_name)
    value=tag[0].firstChild.data.strip()
    return value

def remove_file(filename):
    """
    Delete a file or link, and report this action to the log.
    Arguments:
        filename -- file to remove.
    """
    preexisting=glob.glob(filename)
    if len(preexisting) > 0:
        # Send to log.
        if os.path.islink(filename):
            log_info_mssg(str().join(['Removing link:  ', filename]))
        else:
            log_info_mssg(str().join(['Removing file:  ', filename]))
        os.remove(filename)

def check_abs_path(directory_path):
    """
    Check if directory is absolute path.
    If not, prepend current working directory.
        Argument:
            directory_path -- path to check if absolute
    """
    if directory_path[0] != '/':
        directory_path = os.getcwd() +'/' + directory_path
    
    return directory_path
    
def add_trailing_slash(directory_path):
    """
    Add trailing slash if one is not already present.
    Argument:
        directory_path -- path to which trailing slash should be confirmed.
    """
    # Add trailing slash.
    if directory_path[-1] != '/':
        directory_path=str().join([directory_path, '/'])
    # Return directory_path with trailing slash.
    return directory_path

def verify_directory_path_exists(directory_path, variable_name, sigevent_url):
    """
    Verify that directory_path exists.
    Argument:
        directory_path -- path whose existence needs to be verified.
    """
    if not os.path.isdir(directory_path):
        mssg=str().join([variable_name, ' ', directory_path, 
                         ' does not exist.'])
        log_sig_exit('ERROR', mssg, sigevent_url)

def get_input_files(dom):
    """
    Returns comma-separated list of files from <input_files> element.
    Arguments:
        dom -- The XML dom in which to retrieve <input_files> element.
    """
    files = []
    input_file_element = dom.getElementsByTagName("input_files")[0]
    file_elements = input_file_element.getElementsByTagName("file")
    if len(file_elements) > 0:
        for element in file_elements:
            files.append(check_abs_path(element.firstChild.data.strip()))
    else:
        files.append(check_abs_path(input_file_element.firstChild.data.strip())) 
    return ",".join(files)

def get_doy_string(date_of_data):
    """
    Convert date_of_data string into three-digit doy string.
    Argument:
        date_of_data -- string variable, example: 20120730
    """
    y=int(date_of_data[0:4])
    m=int(date_of_data[4:6])
    d=int(date_of_data[6:8])
    doy=str(datetime.datetime(y, m, d).timetuple().tm_yday)
    if int(doy) < 10:
        doy=str().join(['00', str(int(doy))])
    elif int(doy) < 100:
        doy=str().join(['0', str(int(doy))])
    return doy

def run_command(cmd, sigevent_url):
    """
    Runs the provided command on the terminal.
    Arguments:
        cmd -- the command to be executed.
    """
    log_info_mssg(' '.join(cmd))
    process = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    process.wait()
    for output in process.stdout:
        log_info_mssg(output.strip())
    for error in process.stderr:
        log_sig_err(error.strip(), sigevent_url)
        raise Exception(error.strip())
    