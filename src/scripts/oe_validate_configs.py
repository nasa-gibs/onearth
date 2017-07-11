#!/bin/env python

# Copyright (c) 2002-2017, California Institute of Technology.
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

# Tool for validating OnEarth layer configurations

import os
import sys
import re
import glob
import difflib
import shutil
from optparse import OptionParser
from oe_utils import *
from parse_apache_configs import parse_config
from pyparsing import ParseException

versionNumber = '1.3.1'

# List of allowed directives
allowed_apache_directives = ["WMTSWrapperRole", "WMTSWrapperEnableTime", "WMTSWrapperMimeType", "Reproject_RegExp", "Reproject_ConfigurationFiles", "tWMS_RegExp", "tWMS_ConfigurationFile"]

# Directive regular expressions
WMTSWrapperRole = re.compile(r"^(root|layer|style|tilematrixset)")
WMTSWrapperEnableTime = re.compile(r"^(on|off)")
WMTSWrapperMimeType = re.compile(r"^image/(png|jpeg|tiff|lerc)")
ReprojectRegExp = re.compile(r"^GoogleMapsCompatible_Level[0-9]{1,2}/\\d\{1,2\}/\\d\{1,3\}/\\d\{1,3\}\.(png|\(jpg\|jpeg\)|tiff|lerc)\$")
ReprojectConfigurationFiles = re.compile(r"^.+_source\.config .+_reproject\.config")
tWMSRegExp = re.compile(r"^twms\.cgi")
tWMSConfigurationFile = re.compile(r".+/\${layer}/twms\.config")

Size = re.compile(r"^[0-9]+\s?[0-9]+\s?[0-9]*\s?[0-9]*")
PageSize = re.compile(r"^[0-9]+ [0-9]+")
SkippedLevels = re.compile(r"^[0-9]{1,2}")
BoundingBox = re.compile(r"^-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+")
Projection = re.compile(r"^EPSG:[0-9][0-9][0-9][0-9]")
Nearest = re.compile(r"^(On|Off)")
SourcePostfix = re.compile(r"\.(png|jpg|jpeg|\(jpg\|jpeg\)|tiff|lerc|pbf)")
MimeType = re.compile(r"^image/(png|jpeg|tiff|lerc)")
Oversample = re.compile(r"^(On|Off)")
ExtraLevels = re.compile(r"^[0-9]{1,2}")
Quality = re.compile(r"^[0-9]{1,2}")

# Add regular expressions to lookup dictionary
directive_rules = {}
directive_rules["WMTSWrapperRole"] = WMTSWrapperRole
directive_rules["WMTSWrapperEnableTime"] = WMTSWrapperEnableTime
directive_rules["WMTSWrapperMimeType"] = WMTSWrapperMimeType
directive_rules["ReprojectRegExp"] = ReprojectRegExp
directive_rules["ReprojectConfigurationFiles"] = ReprojectConfigurationFiles
directive_rules["tWMSRegExp"] = tWMSRegExp
directive_rules["tWMSConfigurationFile"] = tWMSConfigurationFile

def parse_apache_config(filename, env, sigevent_url, verbose):
    errors = 0
    msg = []
    
    try:
        apache_config = open(filename, 'r')
        if verbose:
            print ('Opening config file: ' + filename + '\n')
    except IOError:
        errors += 1
        error_msg = "Cannot read Apache configuration file: " + filename
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        return errors, error_msg
    
    apache_config_str = apache_config.read()
    # parse config doesn't like underscores in directives
    for directive in allowed_apache_directives:
        if "_" in directive:
            apache_config_str = apache_config_str.replace(directive, directive.replace("_",""))
    apache_config.close()
    
    # Check for either TWMS or WMTS (default) service type
    service_type = "wmts"
    if "twms" in filename.lower():
        service_type = "twms"
    
    try:
        apache_parse_obj = parse_config.ParseApacheConfig(apache_file_as_string=apache_config_str)
        apache_config = apache_parse_obj.parse_config()
        
        for top_directive in apache_config:
            result = eval_top_directive(top_directive, env, service_type, sigevent_url, verbose)
            errors += result[0]
            msg += result[1]
    except ParseException:
        errors += 1
        error_msg = "Invalid Apache configuration - unable to parse " + filename
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
    
    error_msg = "\n" + str(errors) + " errors found:\n" + "\n".join(msg)
    
    return errors, error_msg
    
def parse_oe_layer_config(filename, env, sigevent_url, verbose):
    errors = 0
    msg = []
    
    try:
        layer_config=open(filename, 'r')
        if verbose:
            print ('\nUsing OnEarth later config: ' + filename + '\n')
        layer_config.close()
        print "OnEarth layer configuration validation is not yet supported"
    except IOError:
        errors += 1
        error_msg = "Cannot read OnEarth layer configuration file: " + filename
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
    
    error_msg = "\n" + str(errors) + " errors found:\n" + "\n".join(msg)
        
    return errors, error_msg
    
def eval_top_directive (directive, env, service_type, sigevent_url, verbose, allowed_apache_directives=allowed_apache_directives):
    errors = 0
    msg = []

    # Make sure we really have a top directive
    if hasattr(directive, "open_tag"):

        # Only <Directory> top-level directives are acceptable
        if directive.open_tag.startswith("<Directory") == False and directive.close_tag.endswith("</Directory>") == False:
            errors += 1
            error_msg = directive.open_tag + " is not allowed"
            msg.append(error_msg)
            log_sig_err(error_msg, sigevent_url)
        else:
            if verbose:
                print "Validating " + directive.open_tag
            directory = add_trailing_slash(directive.open_tag.replace("<Directory ","").replace(">",""))
            if service_type == "wmts":
                if directory.startswith(env.reprojectLayerConfigLocation_wmts) == False:
                    errors += 1
                    error_msg = directory + " does not match ReprojectLayerConfigLocation: " + env.reprojectLayerConfigLocation_wmts
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                else:
                    for d in directive:
                        result = eval_directive(d, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
            else:
                if directory.startswith(env.reprojectLayerConfigLocation_twms.replace("/.lib", "")) == False:
                    errors += 1
                    error_msg = directory + " does not match ReprojectLayerConfigLocation: " + env.reprojectLayerConfigLocation_twms
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                else:
                    for d in directive:
                        result = eval_directive(d, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
    
    elif hasattr(directive, "name"): # directives outside of Directory are not allowed
        errors += 1
        error_msg = directive.name + " directive is not allowed - directives must be in <Directory>"
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        
    return errors, msg
        

def eval_directive (directive, env, service_type, sigevent_url, verbose, allowed_apache_directives=allowed_apache_directives, directive_rules=directive_rules):
    errors = 0
    msg = []
    # parse config doesn't like underscores in directives
    allowed = [w.replace('_', '') for w in allowed_apache_directives]
    
    if directive.name not in allowed:
        errors += 1
        error_msg = directive.name + " directive is not allowed"
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
    else:
        try:
            regex = directive_rules[directive.name]
            research = regex.search(directive.args)
            if research == None:
                errors += 1
                error_msg = "Incorrect pattern found for " + directive.name + " " + directive.args
                msg.append(error_msg)
                log_sig_err(error_msg, sigevent_url)
            else:
                # Evaluate sub-configs
                result = 0, []
                if directive.name == "tWMSConfigurationFile":
                    result = evaluate_tWMSConfigurationFile(directive.args, env, service_type, sigevent_url, verbose)
                elif directive.name == "ReprojectConfigurationFiles":
                    source_config, reproject_config = directive.args.split(" ")
                    result = evaluate_ReprojectConfigurationFiles(source_config, reproject_config, env, service_type, sigevent_url, verbose)
                errors += result[0]
                msg += result[1]
        except KeyError:
            errors += 1
            error_msg = "No patterns for matching are specified for " + directive.name
            msg.append(error_msg)
            log_sig_err(error_msg, sigevent_url)
    
    return errors, msg

def evaluate_tWMSConfigurationFile (config, env, service_type, sigevent_url, verbose):
    errors = 0
    msg = []
    
    # List of allowed directives
    allowed_twms_directives = ["Size", "PageSize", "SkippedLevels", "BoundingBox", "SourcePath", "SourcePostfix"]
    
    # Search for all matching TWMS configs
    config_base_path = config.split("${layer}")[0]
    if verbose:
        print "Search for TWMS configuration files in " + config_base_path
    if not os.path.isdir(config_base_path):
        errors += 1
        error_msg = config_base_path + " is not a valid location"
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        return errors, msg
    else:
        configsearch = config_base_path + "*/*twms.config"
        if len(glob.glob(configsearch)) == 0:
            errors += 1
            error_msg = config + " contains no TWMS config files"
            msg.append(error_msg)
            log_sig_err(error_msg, configsearch)
            return errors, msg
        else:
            for twms_config_file in glob.glob(configsearch):
                # Figure out the correct source path
                source_path = env.reprojectEndpoint_wmts + "/" + twms_config_file.replace(config_base_path,"").replace("twms.config","")
                SourcePath = re.compile(r"^%sdefault/(\$\{date\}\/)?GoogleMapsCompatible_Level[0-9]{1,2}" % source_path)

                # Add regular expressions to lookup dictionary
                twms_directive_rules = {}
                twms_directive_rules["Size"] = Size
                twms_directive_rules["PageSize"] = PageSize
                twms_directive_rules["SkippedLevels"] = SkippedLevels
                twms_directive_rules["BoundingBox"] = BoundingBox
                twms_directive_rules["SourcePath"] = SourcePath
                twms_directive_rules["SourcePostfix"] = SourcePostfix
                
                if verbose:
                    print "Validating " + twms_config_file
                apache_parse_obj = parse_config.ParseApacheConfig(apache_config_path=twms_config_file)
                twms_config = apache_parse_obj.parse_config()
                
                # Evaluate directives
                for directive in twms_config:
                    result = eval_directive(directive, env, service_type, sigevent_url, verbose, allowed_apache_directives=allowed_twms_directives, directive_rules=twms_directive_rules)
                    errors += result[0]
                    msg += result[1]  
    
    return errors, msg

def evaluate_ReprojectConfigurationFiles (source_config, reproject_config, env, service_type, sigevent_url, verbose):
    errors = 0
    msg = []
    
    # Figure out the layer_name from file path
    layer_name = os.path.basename(source_config).replace("_source.config", "")
    
    # Update SourcePath with layer_name
    SourcePath = re.compile(r"^\S+%s/default/(\$\{date\}\/)?\S+" % layer_name)
    
    # Validate source reproject config
    if verbose:
        print "Validating " + source_config
    apache_parse_obj = parse_config.ParseApacheConfig(apache_config_path=source_config)
    source_apache_config = apache_parse_obj.parse_config()
    
    # List of allowed source reproject config directives
    allowed_source_reproject_directives = ["Size", "PageSize", "SkippedLevels", "BoundingBox", "Projection"]

    # Add regular expressions to lookup dictionary
    source_reproject_directive_rules = {}
    source_reproject_directive_rules["Size"] = Size
    source_reproject_directive_rules["PageSize"] = PageSize
    source_reproject_directive_rules["SkippedLevels"] = SkippedLevels
    source_reproject_directive_rules["BoundingBox"] = BoundingBox
    source_reproject_directive_rules["Projection"] = Projection
    
    # Evaluate directives
    for directive in source_apache_config:
        result = eval_directive(directive, env, service_type, sigevent_url, verbose, allowed_apache_directives=allowed_source_reproject_directives, directive_rules=source_reproject_directive_rules)
        errors += result[0]
        msg += result[1]
        
    # Validate source reproject config
    if verbose:
        print "Validating " + reproject_config
    apache_parse_obj = parse_config.ParseApacheConfig(apache_config_path=reproject_config)
    reproject_apache_config = apache_parse_obj.parse_config()
    
    # List of allowed reproject config directives
    allowed_reproject_directives = ["Size", "PageSize", "BoundingBox", "Projection", "Nearest", "SourcePath", "SourcePostfix", "MimeType", "Oversample", "ExtraLevels", "Quality"]

    # Add regular expressions to lookup dictionary
    reproject_directive_rules = {}
    reproject_directive_rules["Size"] = Size
    reproject_directive_rules["PageSize"] = PageSize
    reproject_directive_rules["BoundingBox"] = BoundingBox
    reproject_directive_rules["Projection"] = Projection
    reproject_directive_rules["Nearest"] = Nearest
    reproject_directive_rules["SourcePath"] = SourcePath
    reproject_directive_rules["SourcePostfix"] = SourcePostfix
    reproject_directive_rules["MimeType"] = MimeType
    reproject_directive_rules["Oversample"] = Oversample
    reproject_directive_rules["ExtraLevels"] = ExtraLevels
    reproject_directive_rules["Quality"] = Quality
    
    # Evaluate directives
    for directive in reproject_apache_config:
        result = eval_directive(directive, env, service_type, sigevent_url, verbose, allowed_apache_directives=allowed_reproject_directives, directive_rules=reproject_directive_rules)
        errors += result[0]
        msg += result[1]
    
    return errors, msg

print 'oe_validate_configs.py v' + versionNumber

usageText = 'oe_validate_configs.py --input [input file] --sigevent_url [url] --verbose'

# Define command line options and args.
parser=OptionParser(usage=usageText, version=versionNumber)
parser.add_option('-d', '--diff_file',
                  action='store', type='string', dest='diff_filename',
                  help='Full path existing configuration file to diff')
parser.add_option('-e', '--environment',
                  action='store', type='string', dest='environment_filename',
                  help='Full path of OnEarth environment configuration file')
parser.add_option('-i', '--input',
                  action='store', type='string', dest='input_filename',
                  help='Full path of input configuration file')
parser.add_option('-r', '--replace', action='store_true', dest='replace', 
                  default=False, help="Replace diff_file (after backup) with input if no errors are reported")
parser.add_option('-t', '--type',
                  action='store', type='string', dest='config_type',
                  help='Type of input file: apache or oe_layer')
parser.add_option('-u', '--sigevent_url',
                  action='store', type='string', dest='sigevent_url',
                  default=
                  'http://localhost:8100/sigevent/events/create',
                  help='Default:  http://localhost:8100/sigevent/events/create')
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                  default=False, help="Print out detailed log messages")

# Read command line args
(options, args) = parser.parse_args()

# input filename
if not options.input_filename:
    parser.error('Input filename not provided. --input must be specified.')
else:
    input_filename = check_abs_path(options.input_filename)
    
# diff filename
if not options.diff_filename:
    diff_filename = None
else:
    diff_filename = check_abs_path(options.diff_filename)

# environment filename
if not options.environment_filename:
    environment_filename = "/etc/onearth/config/conf/environment_webmercator.xml"
else:
    environment_filename = check_abs_path(options.environment_filename)
    
# input type
if not options.config_type:
    config_type = "apache"
else:
    if options.config_type.lower() not in ["apache", "oe_layer"]:
        parser.error('type must be one of "apache" or "oe_layer"')
    else:
        config_type = options.config_type.lower()

# replace diff file with input if successful
replace = options.replace

# print verbose log messages
verbose = options.verbose

# Sigevent URL
sigevent_url = options.sigevent_url

# Parse environment
env = get_environment(environment_filename, sigevent_url)

# count errors for return status
errors = 0

# Parse input configuration file
if config_type == "oe_layer":
    errors, error_msg = parse_oe_layer_config(input_filename, env, sigevent_url, options.verbose)
else: # default apache
    errors, error_msg = parse_apache_config(input_filename, env, sigevent_url, options.verbose)
    
if diff_filename != None:
    print "\nExecuting diff with: " + diff_filename + "\n"
    try:
        apache_config = open(input_filename, 'r')
        if verbose:
            print ('Reading config file: ' + input_filename)
        diff_config = open(diff_filename, 'r')
        if verbose:
            print ('Reading config file: ' + diff_filename)
        diff = difflib.ndiff(apache_config.readlines(), diff_config.readlines())
        # print '\n'.join(diff)
        delta = ''.join(x[2:] for x in diff if x.startswith('- '))
        print delta
        apache_config.close()
        diff_config.close()
    except IOError:
        error_msg = "Cannot read diff files " + input_filename + " and " + diff_filename
        log_sig_err(error_msg, sigevent_url)

# Print summary of errors
if errors > 0:
    print error_msg
else:
    print "Validation successful - no errors were found"

if replace:
    if errors == 0:
        print "\nReplacing " + diff_filename + " with " + input_filename + "\n"
        shutil.copyfile(input_filename, diff_filename)
    else:
        log_sig_err("\nUnable to replace " + diff_filename + " with " + input_filename + " due to unsuccessful validation\n", sigevent_url)

print 'oe_validate_configs completed'
sys.exit(errors)
