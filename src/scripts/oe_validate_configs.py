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
WMTSWrapperRole = re.compile(r"^(root|layer|style|tilematrixset)$")
WMTSWrapperEnableTime = re.compile(r"^(on|off)$")
WMTSWrapperMimeType = re.compile(r"^image/(png|jpeg|tiff|lerc)$")
ReprojectRegExp = re.compile(r"^GoogleMapsCompatible_Level[0-9]{1,2}/\\d\{1,2\}/\\d\{1,5\}/\\d\{1,5\}\.(png|\(jpg\|jpeg\)|tiff|lerc)\$$")
ReprojectConfigurationFiles = re.compile(r"^.+_source\.config .+_reproject\.config$")
tWMSRegExp = re.compile(r"^twms\.cgi$")
tWMSConfigurationFile = re.compile(r".+/\${layer}/twms\.config$")

Size = re.compile(r"^[0-9]+\s?[0-9]+\s?[0-9]*\s?[0-9]*$")
PageSize = re.compile(r"^[0-9]+ [0-9]+$")
SkippedLevels = re.compile(r"^[0-9]{1,2}$")
BoundingBox = re.compile(r"^-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+,-?[0-9]+\.?[0-9]+$")
Projection = re.compile(r"^EPSG:[0-9][0-9][0-9][0-9]$")
Nearest = re.compile(r"^(On|Off)$")
SourcePostfix = re.compile(r"\.(png|jpg|jpeg|\(jpg\|jpeg\)|tiff|lerc|pbf)$")
MimeType = re.compile(r"^image/(png|jpeg|tiff|lerc)$")
Oversample = re.compile(r"^(On|Off)$")
ExtraLevels = re.compile(r"^[0-9]{1,2}$")
Quality = re.compile(r"^([0-9]{1,2}|100)$")
ETagSeed = re.compile(r"^[0-9a-f]{32}$")

# Add regular expressions to lookup dictionary
directive_rules = {}
directive_rules["WMTSWrapperRole"] = WMTSWrapperRole
directive_rules["WMTSWrapperEnableTime"] = WMTSWrapperEnableTime
directive_rules["WMTSWrapperMimeType"] = WMTSWrapperMimeType
directive_rules["ReprojectRegExp"] = ReprojectRegExp
directive_rules["ReprojectConfigurationFiles"] = ReprojectConfigurationFiles
directive_rules["tWMSRegExp"] = tWMSRegExp
directive_rules["tWMSConfigurationFile"] = tWMSConfigurationFile

def parse_apache_config(filename, env, sigevent_url, verbose, eval_final_location=True, eval_staging_location=True):
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
            result = eval_top_directive(top_directive, env, service_type, filename, sigevent_url, verbose, eval_final_location=eval_final_location, eval_staging_location=eval_staging_location)
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
    
def eval_top_directive (directive, env, service_type, origin_file, sigevent_url, verbose, eval_final_location=True, eval_staging_location=True, allowed_apache_directives=allowed_apache_directives):
    errors = 0
    msg = []

    # Make sure we really have a top directive
    if hasattr(directive, "open_tag"):

        # Only <Directory> top-level directives are acceptable
        if directive.open_tag.startswith("<Directory") == False and directive.close_tag.endswith("</Directory>") == False:
            errors += 1
            error_msg = directive.open_tag + " is not allowed in " + origin_file
            msg.append(error_msg)
            log_sig_err(error_msg, sigevent_url)
        else:
            if verbose:
                print "Validating " + directive.open_tag
            directory = add_trailing_slash(directive.open_tag.replace("<Directory ","").replace(">",""))
            if service_type == "wmts":
                if directory.startswith(str(env.reprojectLayerConfigLocation_wmts)) == False:
                    errors += 1
                    error_msg = directory + " does not match ReprojectLayerConfigLocation: " + str(env.reprojectLayerConfigLocation_wmts) + " in " + origin_file
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                elif '..' in directory:
                    errors += 1
                    error_msg = "Incorrect pattern found for " + directive.open_tag + " in " + origin_file
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                else:
                    for d in directive:
                        # check special roles
                        if d.name == "WMTSWrapperEnableTime":
                            if not any("layer" in d.args for d in directive):
                                errors += 1
                                error_msg = d.name + " is inappropriate for WMTSWrapperRole in " + directive.open_tag + " in " + origin_file
                                msg.append(error_msg)
                                log_sig_err(error_msg, sigevent_url)
                        if d.name == "WMTSWrapperMimeType":
                            if not any("tilematrixset" in d.args for d in directive):
                                errors += 1
                                error_msg = d.name + " is inappropriate for WMTSWrapperRole in " + directive.open_tag + " in " + origin_file
                                msg.append(error_msg)
                                log_sig_err(error_msg, sigevent_url)
                        # evaluate other directives
                        result = eval_directive(d, env, service_type, origin_file, sigevent_url, verbose, eval_final_location=eval_final_location, eval_staging_location=eval_staging_location)
                        errors += result[0]
                        msg += result[1]
            else:
                if directory.startswith(str(env.reprojectLayerConfigLocation_twms)) == False:
                    errors += 1
                    error_msg = directory + " does not match ReprojectLayerConfigLocation: " + str(env.reprojectLayerConfigLocation_twms) + " in " + origin_file
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                elif '..' in directory:
                    errors += 1
                    error_msg = "Incorrect pattern found for " + directive.open_tag + " in " + origin_file
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                else:
                    for d in directive:
                        result = eval_directive(d, env, service_type, origin_file, sigevent_url, verbose, eval_final_location=eval_final_location, eval_staging_location=eval_staging_location)
                        errors += result[0]
                        msg += result[1]
    
    elif hasattr(directive, "name"): # directives outside of Directory are not allowed, except for Alias
        if directive.name == "Alias":
            if len(directive.args.split(" ")) == 2:
                alias_dest, alias_source = directive.args.split(" ")
                # get the layer name
                layer_name = os.path.basename(os.path.normpath(alias_source)).strip("/")
                if service_type == "wmts":
                    # check alias locations match what's expected
                    if alias_dest != add_trailing_slash(str(env.reprojectEndpoint_wmts)) + layer_name:
                        errors += 1
                        error_msg = "Alias destination " + alias_dest + " does not match expected " + add_trailing_slash(str(env.reprojectEndpoint_wmts)) + layer_name + " in " + origin_file
                        msg.append(error_msg)
                        log_sig_err(error_msg, sigevent_url)
                    if alias_source != add_trailing_slash(str(env.reprojectLayerConfigLocation_wmts)) + layer_name:
                        errors += 1
                        error_msg = "Alias source " + alias_source + " does not match expected " + add_trailing_slash(str(env.reprojectLayerConfigLocation_wmts)) + layer_name + " in " + origin_file
                        msg.append(error_msg)
                        log_sig_err(error_msg, sigevent_url)
                else:
                    if alias_dest != str(env.reprojectEndpoint_twms):
                        errors += 1
                        error_msg = "Alias destination " + alias_dest + " does not match expected " + str(env.reprojectEndpoint_twms) + " in " + origin_file
                        msg.append(error_msg)
                        log_sig_err(error_msg, sigevent_url)
                    if alias_source != str(env.reprojectLayerConfigLocation_twms):
                        errors += 1
                        error_msg = "Alias source " + alias_source + " does not match expected " + str(env.reprojectLayerConfigLocation_twms) + " in " + origin_file
                        msg.append(error_msg)
                        log_sig_err(error_msg, sigevent_url)
                # make sure source actually exists
                if not alias_source.endswith("wmts.cgi"):
                    if eval_final_location: # final location must exist to evaluate
                        if not os.path.isdir(alias_source):
                            errors += 1
                            error_msg = alias_source + " is not an accessible directory in " + origin_file
                            msg.append(error_msg)
                            log_sig_err(error_msg, sigevent_url)
                    else:
                        if not os.path.isdir(alias_source.replace(add_trailing_slash(str(env.reprojectLayerConfigLocation_wmts)), add_trailing_slash(str(env.wmts_dir)))): # evaluate staging location instead
                            errors += 1
                            error_msg = alias_source + " is not an accessible directory in " + origin_file
                            msg.append(error_msg)
                            log_sig_err(error_msg, sigevent_url)
            else:
                errors += 1
                error_msg = directive.name + " " + directive.args + " does not contain two parameters in " + origin_file
                msg.append(error_msg)
                log_sig_err(error_msg, sigevent_url)
        else:
            errors += 1
            error_msg = directive.name + " directive is not allowed - directives must be in <Directory> in " + origin_file
            msg.append(error_msg)
            log_sig_err(error_msg, sigevent_url)
        
    return errors, msg
        

def eval_directive (directive, env, service_type, origin_file, sigevent_url, verbose, eval_final_location=True, eval_staging_location=True, allowed_apache_directives=allowed_apache_directives, directive_rules=directive_rules):
    errors = 0
    msg = []
    # parse config doesn't like underscores in directives
    allowed = [w.replace('_', '') for w in allowed_apache_directives]
    
    if directive.name not in allowed:
        errors += 1
        error_msg = directive.name + " directive is not allowed in " + origin_file
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
    else:
        try:
            regex = directive_rules[directive.name]
            research = regex.search(directive.args)
            if research == None:
                errors += 1
                error_msg = "Incorrect pattern found for " + directive.name + " " + directive.args + " in " + origin_file
                msg.append(error_msg)
                log_sig_err(error_msg, sigevent_url)
            else:
                # Evaluate sub-configs
                result = 0, []
                if directive.name == "tWMSConfigurationFile":
                    staging_location = add_trailing_slash(str(env.twms_dir))
                    final_location = add_trailing_slash(str(directive.args).split("${layer}")[0])
                    if eval_final_location:
                        result = evaluate_tWMSConfigurationFile(directive.args, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
                    if eval_staging_location:
                        twms_config = str(directive.args).replace(final_location, staging_location)
                        result = evaluate_tWMSConfigurationFile(twms_config, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
                    if eval_final_location and eval_staging_location: # compare files if we're evaluating both
                        result = diff_configs(twms_config, directive.args, verbose)
                        errors += result[0]
                        msg += result[1]
                        
                elif directive.name == "ReprojectConfigurationFiles":
                    staging_location = add_trailing_slash(str(env.wmts_dir))
                    final_location = add_trailing_slash(str(env.reprojectLayerConfigLocation_wmts))
                    source_config, reproject_config = directive.args.split(" ")
                    if eval_final_location:
                        result = evaluate_ReprojectConfigurationFiles(source_config, reproject_config, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
                    if eval_staging_location:
                        staged_source_config = source_config.replace(final_location, staging_location)
                        staged_reproject_config = reproject_config.replace(final_location, staging_location)
                        result = evaluate_ReprojectConfigurationFiles(staged_source_config, staged_reproject_config, env, service_type, sigevent_url, verbose)
                        errors += result[0]
                        msg += result[1]
                    if eval_final_location and eval_staging_location: # compare files if we're evaluating both
                        result = diff_configs(staged_source_config, source_config, verbose)
                        errors += result[0]
                        msg += result[1]
                        result = diff_configs(staged_reproject_config, reproject_config, verbose)
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
    
    # Evaluate tWMS_ConfigurationFile
    tWMS_ConfigurationFile = re.compile(r"^(%s|%s)(\$\{layer\}\/)twms.config$" % (add_trailing_slash(str(env.reprojectLayerConfigLocation_twms)), add_trailing_slash(env.twms_dir)))
    research = tWMS_ConfigurationFile.search(config)
    if research == None:
        errors += 1
        error_msg = "Incorrect pattern found for tWMS_ConfigurationFile " + config
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        return errors, msg
    
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
                SourcePath = re.compile(r"^%sdefault/(\$\{date\}\/)?GoogleMapsCompatible_Level[0-9]{1,2}$" % source_path)

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
                    result = eval_directive(directive, env, service_type, config, sigevent_url, verbose, allowed_apache_directives=allowed_twms_directives, directive_rules=twms_directive_rules)
                    errors += result[0]
                    msg += result[1]  
    
    return errors, msg

def evaluate_ReprojectConfigurationFiles (source_config, reproject_config, env, service_type, sigevent_url, verbose):
    errors = 0
    msg = []
    
    # Figure out the layer_name from file path
    layer_name = os.path.basename(source_config).replace("_source.config", "")
    
    # Update SourcePath with layer_name
    SourcePath = re.compile(r"^/(?:\w+/)+%s/default/(\$\{date\}\/)?\S+$" % layer_name)
    
    # Validate source reproject config
    if verbose:
        print "Validating " + source_config
    if not os.path.isfile(source_config):
        errors += 1
        error_msg = source_config + " is not a valid location"
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        return errors, msg
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
        result = eval_directive(directive, env, service_type, source_config, sigevent_url, verbose, allowed_apache_directives=allowed_source_reproject_directives, directive_rules=source_reproject_directive_rules)
        errors += result[0]
        msg += result[1]
        
    # Validate source reproject config
    if verbose:
        print "Validating " + reproject_config
    if not os.path.isfile(reproject_config):
        errors += 1
        error_msg = reproject_config + " is not a valid location"
        msg.append(error_msg)
        log_sig_err(error_msg, sigevent_url)
        return errors, msg
    apache_parse_obj = parse_config.ParseApacheConfig(apache_config_path=reproject_config)
    reproject_apache_config = apache_parse_obj.parse_config()
    
    # List of allowed reproject config directives
    allowed_reproject_directives = ["Size", "PageSize", "BoundingBox", "Projection", "Nearest", "SourcePath", "SourcePostfix", "MimeType", "Oversample", "ExtraLevels", "Quality", "ETagSeed"]

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
    reproject_directive_rules["ETagSeed"] = ETagSeed
    
    # Evaluate directives
    for directive in reproject_apache_config:
        result = eval_directive(directive, env, service_type, reproject_config, sigevent_url, verbose, allowed_apache_directives=allowed_reproject_directives, directive_rules=reproject_directive_rules)
        errors += result[0]
        msg += result[1]
    
    return errors, msg

def diff_configs (source_configs, destination_configs, verbose):
    errors = 0
    msg = []
    source_list = []
    destination_list = []
    configs = [("source", source_configs), ("destination", destination_configs)]
    for config_type, config in configs:
        if "${layer}" in config:
            # Search for all configs
            config_base_path = config.split("${layer}")[0]
            if verbose:
                print "Search for configuration files in " + config_base_path
            if not os.path.isdir(config_base_path):
                errors += 1
                error_msg = config_base_path + " is not a valid location"
                msg.append(error_msg)
                log_sig_err(error_msg, sigevent_url)
                return errors, msg
            else:
                configsearch = config_base_path + "*/*.config"
                if len(glob.glob(configsearch)) == 0:
                    errors += 1
                    error_msg = config + " contains no config files"
                    msg.append(error_msg)
                    log_sig_err(error_msg, sigevent_url)
                    return errors, msg
                else:
                    for config_file in glob.glob(configsearch):
                        if config_type == "source":
                            source_list.append(config_file)
                        if config_type == "destination":
                            destination_list.append(config_file)
        else:
            if config_type == "source":
                source_list.append(config)
            if config_type == "destination":
                destination_list.append(config)
    for idx, destination_config in enumerate(destination_list):
        source_config = source_list[idx]
        if verbose:
            print "Comparing " + source_config + " with " + destination_config
        try:
            source_file = open(source_config, 'r')
            if verbose:
                print ('Reading config file: ' + source_config)
            destination_file = open(destination_config, 'r')
            if verbose:
                print ('Reading config file: ' + destination_config)
            diff = difflib.ndiff(source_file.readlines(), destination_file.readlines())
            delta = ''.join(x[2:] for x in diff if x.startswith('- '))
            source_file.close()
            destination_file.close()
            if len(delta) > 0:
                warn_msg = source_config + " and " + destination_config + " files differ:\n" + delta
                log_sig_warn(warn_msg, sigevent_url)
        except IOError:
            errors += 1
            error_msg = "Cannot compare files " + source_config + " and " + destination_config
            log_sig_err(error_msg, sigevent_url)
            msg.append(error_msg)
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
parser.add_option("-S", "--ignore_staged_files", action="store_true", dest="ignore_staged_files", 
                  default=False, help="Do not validate configurations in staging location")
parser.add_option("-F", "--ignore_final_files", action="store_true", dest="ignore_final_files", 
                  default=False, help="Do not validate configurations in final config locations; evaluate staged files only")

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
# Add leading slashes to reproject endpoints
if env.reprojectEndpoint_wmts is not None:
    if not env.reprojectEndpoint_wmts.startswith('/'):
        env.reprojectEndpoint_wmts = '/' + env.reprojectEndpoint_wmts
if env.reprojectEndpoint_twms is not None:
    if not env.reprojectEndpoint_twms.startswith('/'):
        env.reprojectEndpoint_twms = '/' + env.reprojectEndpoint_twms

# count errors for return status
errors = 0

# Parse input configuration file
if config_type == "oe_layer":
    errors, error_msg = parse_oe_layer_config(input_filename, env, sigevent_url, options.verbose)
else: # default apache
    errors, error_msg = parse_apache_config(input_filename, env, sigevent_url, options.verbose, eval_final_location = not options.ignore_final_files, eval_staging_location = not options.ignore_staged_files)
    
if diff_filename is not None:
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
        delta = ''.join(x for x in diff if x.startswith('- ') or x.startswith('+ '))
        print '\n' + delta
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
if errors == 0:
    sys.exit(0)
else:
    sys.exit(1)
