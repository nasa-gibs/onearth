#!/usr/bin/env python3

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

#
# Pipeline for converting vector-based datasets into standardized vector tiles, rasterized tiles, and GeoJSON.
#
# Example:
#
#  vectorgen.py
#   -c vectorgen_configuration_file.xml

from optparse import OptionParser
from oe_utils import *
from oe_create_mvt_mrf import create_vector_mrf
from datetime import datetime
import glob
import logging
import os
import sys
import time
import xml.dom.minidom
import shutil
import re
try:
    from osgeo import ogr, osr, gdal
except:
    sys.exit('ERROR: cannot find GDAL/OGR modules')

versionNumber = os.environ.get('ONEARTH_VERSION')
basename = None

def geojson2shp(in_filename, out_filename, source_epsg, target_epsg, sigevent_url):
    """
    Converts GeoJSON into Esri Shapefile.
    Arguments:
        in_filename -- the input GeoJSON
        out_filename -- the output Shapefile
        source_epsg -- the EPSG code of source file
        target_epsg -- the EPSG code of target file
        sigevent_url -- the URL for SigEvent
    """
    if source_epsg == target_epsg:
        ogr2ogr_command_list = ['ogr2ogr', '-f', 'ESRI Shapefile', '-fieldTypeToString', 'Date,Time,DateTime', out_filename, in_filename]
    else:
        ogr2ogr_command_list = ['ogr2ogr', '-f', 'ESRI Shapefile', '-fieldTypeToString', 'Date,Time,DateTime', '-s_srs', source_epsg, '-t_srs', target_epsg, out_filename, in_filename]
    run_command(ogr2ogr_command_list, sigevent_url)

def shp2geojson(in_filename, out_filename, source_epsg, target_epsg, sigevent_url):
    """
    Converts Esri Shapefile into GeoJSON.
    Arguments:
        in_filename -- the input Shapefile
        out_filename -- the output GeoJSON file
        source_epsg -- the EPSG code of source file
        target_epsg -- the EPSG code of target file
        sigevent_url -- the URL for SigEvent
    """
    if source_epsg == target_epsg:
        ogr2ogr_command_list = ['ogr2ogr', '-f', 'GeoJSON', out_filename, in_filename]
    else:
        ogr2ogr_command_list = ['ogr2ogr', '-f', 'GeoJSON', '-s_srs', source_epsg, '-t_srs', target_epsg, out_filename, in_filename]
    run_command(ogr2ogr_command_list, sigevent_url)


def parse_filter(elem):
    name = elem.getAttribute('name')
    if not name:
        raise ValueError('No "name" attribute found for {0} element'.format(elem.nodeName))

    value = elem.getAttribute('value')
    regexp_str = elem.getAttribute('regexp')
    regexp = None
    if regexp_str:
        try:
            regexp = re.compile(regexp_str)
        except:
            print("ERROR -- problem compiling regexp string {0}. Make sure it's a valid Python regular expression.".format(
                regexp_str))
            sys.exit()
    if not value and not regexp:
        raise ValueError('No "value" or "regexp" attribute found for {0} element'.format(elem.nodeName))

    if elem.nodeName in ['ge', 'gt', 'le', 'lt']:
        try:
            value = float(value)
        except:
            raise ValueError('"value" attribute must be numerical')

    return {'comparison': elem.nodeName, 'name': name, 'value': value, 'regexp': regexp}


if __name__ == '__main__':

    # Declare counter for errors
    errors = 0

    # Define command line options and args.
    parser = OptionParser(version = versionNumber)
    parser.add_option('-c', '--configuration_filename',
                      action='store', type='string', dest='configuration_filename',
                      default='./vectorgen_configuration_file.xml',
                      help='Full path of configuration filename.  Default:  ./vectorgen_configuration_file.xml')
    parser.add_option("-s", "--send_email", action="store_true", dest="send_email",
                      default=False, help="Send email notification for errors and warnings.")
    parser.add_option('--email_server', action='store', type='string', dest='email_server',
                      default='', help='The server where email is sent from (overrides configuration file value)')
    parser.add_option('--email_recipient', action='store', type='string', dest='email_recipient',
                      default='', help='The recipient address for email notifications (overrides configuration file value)')
    parser.add_option('--email_sender', action='store', type='string', dest='email_sender',
                      default='', help='The sender for email notifications (overrides configuration file value)')
    parser.add_option('--email_logging_level', action='store', type='string', dest='email_logging_level',
                  default='ERROR', help='Logging level for email notifications: ERROR, WARN, or INFO.  Default: ERROR')

    # Read command line args.
    (options, args) = parser.parse_args()
    # Configuration filename.
    configuration_filename=options.configuration_filename
    # Send email.
    send_email=options.send_email
    # Email server.
    email_server=options.email_server
    # Email recipient
    email_recipient=options.email_recipient
    # Email sender
    email_sender=options.email_sender
    # Email logging level
    logging_level = options.email_logging_level.upper()
    # Email metadata replaces sigevent_url
    if send_email:
        sigevent_url = (email_server, email_recipient, email_sender, logging_level)
    else:
        sigevent_url = ''

    # Get current time, which is written to a file as the previous cycle time.
    # Time format is "yyyymmdd.hhmmss".  Do this first to avoid any gap where tiles
    # may get passed over because they were created while this script is running.
    current_cycle_time=time.strftime('%Y%m%d.%H%M%S', time.localtime())

    # Read XML configuration file.
    try:
        # Open file.
        config_file=open(configuration_filename, 'r')
    except IOError:
        mssg=str().join(['Cannot read configuration file:  ', configuration_filename])
        log_sig_exit('ERROR', mssg, sigevent_url)
    else:
        # Get dom from XML file.
        dom=xml.dom.minidom.parse(config_file)
        # Parameter name.
        parameter_name = get_dom_tag_value(dom, 'parameter_name')
        date_of_data = get_dom_tag_value(dom, 'date_of_data')

        # Define output basename
        basename=str().join([parameter_name, '_', date_of_data, '___', 'vectorgen_', current_cycle_time, '_', str(os.getpid())])

        # Get default email server and recipient if not override
        if email_server == '':
            try:
                email_server = get_dom_tag_value(dom, 'email_server')
            except:
                email_server = ''
        if email_recipient == '':
            try:
                email_recipient = get_dom_tag_value(dom, 'email_recipient')
            except:
                email_recipient = ''
        if email_sender == '':
            try:
                email_sender = get_dom_tag_value(dom, 'email_sender')
            except:
                email_sender = ''
        if send_email:
            sigevent_url = (email_server, email_recipient, email_sender, logging_level)
            if email_recipient == '':
                log_sig_err("No email recipient provided for notifications.", sigevent_url)

        # for sub-daily imagery
        try:
            time_of_data = get_dom_tag_value(dom, 'time_of_data')
        except:
            time_of_data = ''
        # Directories.
        try:
            input_dir = get_dom_tag_value(dom, 'input_dir')
        except:
            input_dir = None
        output_dir = get_dom_tag_value(dom, 'output_dir')
        try:
            working_dir = get_dom_tag_value(dom, 'working_dir')
            working_dir = add_trailing_slash(check_abs_path(working_dir))
        except: # use /tmp/ as default
            working_dir ='/tmp/'
        try:
            logfile_dir = get_dom_tag_value(dom, 'logfile_dir')
        except: #use working_dir if not specified
            logfile_dir = working_dir
        try:
            output_name = get_dom_tag_value(dom, 'output_name')
        except:
            # default to GIBS naming convention
            output_name = '{$parameter_name}%Y%j_'
        output_format = get_dom_tag_value(dom, 'output_format').lower()
        # EPSG code projection.
        try:
            target_epsg = 'EPSG:' + str(get_dom_tag_value(dom, 'target_epsg'))
        except:
            target_epsg = 'EPSG:4326' # default to geographic
        try:
            source_epsg = 'EPSG:' + str(get_dom_tag_value(dom, 'source_epsg'))
        except:
            source_epsg = 'EPSG:4326' # default to geographic

        # Unique feature id property name
        try:
            feature_id = get_dom_tag_value(dom, "feature_id")

            # Create the unique feature id during processing
            try:
                if get_dom_attr_value(dom, "feature_id", "create") == "true":
                    create_feature_id = True
                else:
                    create_feature_id = False
            except:
                create_feature_id = False
        except:
            feature_id = "UID"
            create_feature_id = True

        # Rate at which to reduce features
        try:
            feature_reduce_rate = float(get_dom_tag_value(dom, 'feature_reduce_rate'))
        except:
            feature_reduce_rate = 0
        # Rate at which to reduce sub-pixel feature clusters
        try:
            cluster_reduce_rate = float(get_dom_tag_value(dom, 'cluster_reduce_rate'))
        except:
            cluster_reduce_rate = 0
        # Input files.
        try:
            input_files = get_input_files(dom)
            if input_files == '':
                raise ValueError('No input files provided')
        except:
            if input_dir == None:
                log_sig_exit('ERROR', "<input_files> or <input_dir> is required", sigevent_url)
            else:
                input_files = ''

        # Identifier for MVT tile content
        try:
            tile_layer_name = get_dom_tag_value(dom, "identifier")
        except:
            tile_layer_name = parameter_name

        # Buffer size
        try:
            buffer_size = float(get_dom_tag_value(dom, "buffer_size"))
        except:
            buffer_size = 5

        # Buffer on the edges
        try:
            if get_dom_attr_value(dom, "buffer_size", "edges") == "false":
                buffer_edges = False
            else:
                buffer_edges = True
        except:
            buffer_edges = False

        # Feature Filtering options
        feature_filters = []
        filter_options = dom.getElementsByTagName('feature_filters')
        if len(filter_options):
            for filter_element in filter_options[0].getElementsByTagName('filter_block'):
                # Validate filter logic
                logic = filter_element.getAttribute('logic')
                if not logic:
                    raise ValueError('"logic" attribute not provided for <filter_block>')
                if logic.lower() != "and" and logic.lower() != "or":
                    raise ValueError('Invalid value for "logic" attribute -- must be AND or OR')

                # Get filters
                comparisons = filter_element.getElementsByTagName('equals') + \
                              filter_element.getElementsByTagName('notEquals') + \
                              filter_element.getElementsByTagName('lt') + \
                              filter_element.getElementsByTagName('le') + \
                              filter_element.getElementsByTagName('gt') + \
                              filter_element.getElementsByTagName('ge')
                filters = list(map(parse_filter, comparisons))
                feature_filters.append({'logic': logic, 'filters': filters})

        # Overview filtering options
        overview_filters = {}
        filter_options = dom.getElementsByTagName('overview_filters')
        if len(filter_options):
            for filter_element in filter_options[0].getElementsByTagName('filter_block'):
                # Validate filter logic
                logic = filter_element.getAttribute('logic')
                if not logic:
                    raise ValueError('"logic" attribute not provided for <filter_block>')
                if logic.lower() != "and" and logic.lower() != "or":
                    raise ValueError('Invalid value for "logic" attribute -- must be AND or OR')

                # Validate filter zoom level
                zLevel = filter_element.getAttribute('zoom')
                if not zLevel:
                    raise ValueError('"zoom" attribute not provided for <filter_block>')
                else:
                    try:
                        int(zLevel)
                    except:
                        raise ValueError('"zoom" attribute must be integer')

                # Get filters
                comparisons = filter_element.getElementsByTagName('equals') + \
                              filter_element.getElementsByTagName('notEquals') + \
                              filter_element.getElementsByTagName('lt') + \
                              filter_element.getElementsByTagName('le') + \
                              filter_element.getElementsByTagName('gt') + \
                              filter_element.getElementsByTagName('ge')
                filters = list(map(parse_filter, comparisons))

                if zLevel not in overview_filters:
                    overview_filters[zLevel] = []
                overview_filters[zLevel].append({'logic': logic, 'filters': filters})

        if output_format not in ['mvt-mrf', 'esri shapefile', 'geojson']:
            log_sig_warn(output_format + ' output format not supported, using "MVT-MRF" instead', sigevent_url)
            output_format = 'mvt-mrf'
        if output_format == 'mvt-mrf':
            try:
                target_x = int(get_dom_tag_value(dom, 'target_x'))
            except IndexError:
                log_sig_exit('ERROR', '<target_x> is required but not specified', sigevent_url)
            except ValueError:
                log_sig_exit('ERROR', '<target_x> value is invalid', sigevent_url)
            try:
                target_y = int(get_dom_tag_value(dom, 'target_y'))
            except IndexError:
                target_y = None
            except ValueError:
                log_sig_exit('ERROR', '<target_y> value is invalid', sigevent_url)
            try:
                target_extents_str = get_dom_tag_value(dom, 'target_extents')
                if len(target_extents_str.split(',')) == 4:
                    target_extents = [float(extent) for extent in target_extents_str.split(',')]
                elif len(target_extents_str.split(' ')) == 4:
                    target_extents = [float(extent) for extent in target_extents_str.split(' ')]
                else:
                    log_sig_exit('ERROR', 'Invalid <target_extents> value -- must be comma or space-separated')
            except IndexError:
                target_extents = (-180, -90, 180, 90)
                log_sig_warn('<target_extents> not specified, assuming -180, -90, 180, 90', sigevent_url)
            except ValueError:
                log_sig_exit('ERROR', 'Problem processing <target_extents>, must be comma or space-separated list.', sigevent_url)
            try:
                tile_size = int(get_dom_tag_value(dom, 'tile_size'))
            except IndexError:
                tile_size = 512
                log_sig_warn('<tile_size> not specified, assuming 512', sigevent_url)
            except ValueError:
                log_sig_exit('ERROR', 'Invalid <tile_size> specified', sigevent_url)
            try:
                overview_levels_str = get_dom_tag_value(dom, 'overview_levels')
                sep = ',' if ',' in overview_levels_str else ' '
                overview_levels = [int(level) for level in overview_levels_str.split(sep)]
            except IndexError:
                overview_levels = None
        # Close file.
        config_file.close()

    # Make certain each directory exists and has a trailing slash.
    if input_dir != None:
        input_dir = add_trailing_slash(check_abs_path(input_dir))
    output_dir = add_trailing_slash(check_abs_path(output_dir))
    logfile_dir = add_trailing_slash(check_abs_path(logfile_dir))

    # Save script_dir
    script_dir = add_trailing_slash(os.path.dirname(os.path.abspath(__file__)))

    # Verify logfile_dir first so that the log can be started.
    verify_directory_path_exists(logfile_dir, 'logfile_dir', sigevent_url)
    # Initialize log file.
    log_filename=str().join([logfile_dir, basename, '.log'])
    logging.basicConfig(filename=log_filename, level=logging.INFO)

    # Verify remaining directory paths.
    if input_dir != None:
        verify_directory_path_exists(input_dir, 'input_dir', sigevent_url)
    verify_directory_path_exists(output_dir, 'output_dir', sigevent_url)
    verify_directory_path_exists(working_dir, 'working_dir', sigevent_url)

    # Log all of the configuration information.
    log_info_mssg_with_timestamp(str().join(['config XML file:                ', configuration_filename]))
    # Copy configuration file to working_dir (if it's not already there) so that the output can be recreated if needed.
    if os.path.dirname(configuration_filename) != os.path.dirname(working_dir):
        config_preexisting=glob.glob(configuration_filename)
        if len(config_preexisting) > 0:
            at_dest_filename=str().join([working_dir, configuration_filename])
            at_dest_preexisting=glob.glob(at_dest_filename)
            if len(at_dest_preexisting) > 0:
                remove_file(at_dest_filename)
            shutil.copy(configuration_filename, working_dir+"/"+basename+".configuration_file.xml")
            log_info_mssg(str().join([
                              'config XML file copied to       ', working_dir]))
    log_info_mssg(str().join(['config parameter_name:          ', parameter_name]))
    log_info_mssg(str().join(['config date_of_data:            ', date_of_data]))
    log_info_mssg(str().join(['config time_of_data:            ', time_of_data]))
    if input_files != '':
        log_info_mssg(str().join(['config input_files:             ', input_files]))
    if input_dir != None:
        log_info_mssg(str().join(['config input_dir:               ', input_dir]))
    log_info_mssg(str().join(['config output_dir:              ', output_dir]))
    log_info_mssg(str().join(['config working_dir:             ', working_dir]))
    log_info_mssg(str().join(['config logfile_dir:             ', logfile_dir]))
    log_info_mssg(str().join(['config output_name:             ', output_name]))
    log_info_mssg(str().join(['config output_format:           ', output_format]))
    if output_format == 'mvt-mrf':
        log_info_mssg(str().join(['config tile_layer_name:         ', tile_layer_name]))
        log_info_mssg(str().join(['config target_x:                ', str(target_x)]))
        log_info_mssg(str().join(['config target_y:                ', str(target_y) if target_y else 'Not specified']))
        log_info_mssg(str().join(['config target_extents:          ', str(target_extents)]))
        log_info_mssg(str().join(['config overview_levels:         ', str(overview_levels)]))
    log_info_mssg(str().join(['config feature_id:              ', str(feature_id)]))
    log_info_mssg(str().join(['config create_feature_id:       ', str(create_feature_id)]))
    log_info_mssg(str().join(['config feature_reduce_rate:     ', str(feature_reduce_rate)]))
    log_info_mssg(str().join(['config cluster_reduce_rate:     ', str(cluster_reduce_rate)]))
    log_info_mssg(str().join(['config buffer_size:             ', str(buffer_size)]))
    log_info_mssg(str().join(['config buffer_edges:            ', str(buffer_edges)]))
    log_info_mssg(str().join(['config target_epsg:             ', target_epsg]))
    log_info_mssg(str().join(['config source_epsg:             ', source_epsg]))
    log_info_mssg(str().join(['vectorgen current_cycle_time:   ', current_cycle_time]))
    log_info_mssg(str().join(['vectorgen basename:             ', basename]))

    # Verify that date is 8 characters.
    if len(date_of_data) != 8:
        mssg='Format for <date_of_data> (in vectorgen XML config file) is:  yyyymmdd'
        log_sig_exit('ERROR', mssg, sigevent_url)

    if time_of_data != '' and len(time_of_data) != 6:
        mssg='Format for <time_of_data> (in vectorgen XML config file) is:  HHMMSS'
        log_sig_exit('ERROR', mssg, sigevent_url)

    # Change directory to working_dir.
    os.chdir(working_dir)

    # Get list of all tile filenames.
    alltiles = []
    if input_files != '':
        input_files = input_files.strip()
        alltiles = input_files.split(',')
    if input_dir != None: # search for only .shp or json/geojson files
        alltiles = alltiles + glob.glob(str().join([input_dir, '*.shp']))
        alltiles = alltiles + glob.glob(str().join([input_dir, '*json']))

    striptiles = []
    for tile in alltiles:
        striptiles.append(tile.strip())
    alltiles = striptiles

    if len(time_of_data) == 6:
        mrf_date = datetime.strptime(str(date_of_data)+str(time_of_data),"%Y%m%d%H%M%S")
    else:
        mrf_date = datetime.strptime(date_of_data, "%Y%m%d")
    out_filename = output_name.replace('{$parameter_name}', parameter_name)
    time_params = []
    for i, char in enumerate(out_filename):
        if char == '%':
            time_params.append(char+out_filename[i+1])
    for time_param in time_params:
        out_filename = out_filename.replace(time_param ,datetime.strftime(mrf_date,time_param))

    out_basename = working_dir + basename
    out_filename = output_dir + out_filename

    if len(alltiles) > 0:
        if output_format == 'esri shapefile':
            for tile in alltiles:
                geojson2shp(tile, out_basename, source_epsg, target_epsg, sigevent_url)
                files = glob.glob(out_basename+"/*")
                for sfile in files:
                    title, ext = os.path.splitext(os.path.basename(sfile))
                    log_info_mssg(str().join(['Moving ', out_basename+"/"+title+ext, ' to ', out_filename+ext]))
                    shutil.move(out_basename+"/"+title+ext, out_filename+ext)
                shutil.rmtree(out_basename)
                mssg=str().join(['Output created:  ', out_filename+".shp"])

        elif output_format == 'mvt-mrf': # Create MVT-MRF
            for idx, tile in enumerate(alltiles):
                # create_vector_mrf can handle GeoJSON and Shapefile, but the file's projection has to match the desired output
                if source_epsg != target_epsg:
                    outfile = os.path.join(working_dir, basename + '_reproject_' + str(idx) + os.path.splitext(tile)[1])
                    ogr2ogr_command_list = ['ogr2ogr', '-preserve_fid', '-f', "GeoJSON" if "json" in os.path.splitext(tile)[1]
                        else "ESRI Shapefile", '-s_srs', source_epsg, '-t_srs', target_epsg, outfile, tile]
                    run_command(ogr2ogr_command_list, sigevent_url)
                    alltiles[idx] = outfile
            log_info_mssg("Creating vector mrf with " + ', '.join(alltiles))
            success = create_vector_mrf(alltiles, working_dir, basename, tile_layer_name, target_x, target_y,
                                        target_extents, tile_size, overview_levels, target_epsg, feature_filters, overview_filters,
                                        feature_id, create_feature_id, feature_reduce_rate=feature_reduce_rate,
                                        cluster_reduce_rate=cluster_reduce_rate,
                                        buffer_size=buffer_size, buffer_edges=buffer_edges, debug=False)
            if not success: errors += 1

            files = [os.path.join(working_dir, basename + ".mrf"),
                     os.path.join(working_dir, basename + ".idx"),
                     os.path.join(working_dir, basename + ".pvt")]

            for mfile in files:
                title, ext = os.path.splitext(os.path.basename(mfile))
                if ext not in [".log",".xml"]:
                    log_info_mssg(str().join(['Moving ', os.path.join(working_dir, title+ext), ' to ', out_filename+ext]))
                    if os.path.isfile(out_filename+ext):
                        log_sig_warn(out_filename + ext + " already exists...overwriting", sigevent_url)
                        os.remove(out_filename + ext)
                    shutil.move(os.path.join(working_dir, title+ext), out_filename+ext)
            mssg=str().join(['Output created:  ', out_filename+".mrf"])

        elif output_format == 'geojson':
            print(alltiles)
            for tile in alltiles:
                shp2geojson(tile, out_basename+".json", source_epsg, target_epsg, sigevent_url)
                shutil.move(out_basename+".json", out_filename+".json")
                mssg=str().join(['Output created:  ', out_filename+".json"])
    else:
        log_sig_exit('ERROR', "No valid input files found", sigevent_url)

    # Send to log.
    try:
        log_info_mssg(mssg)
        # sigevent('INFO', mssg, sigevent_url)
    except urllib.error.URLError:
        None

    sys.exit(errors)
