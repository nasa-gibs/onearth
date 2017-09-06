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
This file contains various utilities for the OnEarth test routines.
"""

import os
import subprocess
from shutil import copyfile, copy
import xml.dom.minidom
import hashlib
import shlex
from dateutil.relativedelta import relativedelta
import sqlite3
import urllib2
import StringIO
import gzip
import mapbox_vector_tile
from lxml import etree
import requests
import sys
# cElementTree deprecated in python 3.3
from xml.etree import cElementTree as ElementTree

class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)

class XmlDictConfig(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''
    def __init__(self, parent_element):
        childrenNames = [child.tag for child in parent_element.getchildren()]

        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))

                if childrenNames.count(element.tag) > 1:
                    try:
                        currentValue = self[element.tag]
                        currentValue.append(aDict)
                        self.update({element.tag: currentValue})
                    except: #the first of its kind, an empty list must be created
                        self.update({element.tag: [aDict]}) #aDict is written in [], i.e. it will be a list

                else:
                    self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
                #self[element.tag].update({"__Content__":element.text})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                if childrenNames.count(element.tag) > 1:
                    try:
                        currentValue = self[element.tag]
                        currentValue.append(element.text)
                        self.update({element.tag: currentValue})
                    except: #the first of its kind, an empty list must be created
                        self.update({element.tag: [element.text]}) # text is written in [], i.e. it will be a list

                #self.update({element.tag: element.text})

def add_trailing_slash(directory_path):
    """
    Add trailing slash if one is not already present.
    Argument:
        directory_path -- path to which trailing slash should be confirmed.
    """
    # Add trailing slash.
    if directory_path[-1] != '/':
        directory_path = str().join([directory_path, '/'])
    # Return directory_path with trailing slash.
    return directory_path


def restart_apache():
    try:
        check_apache_running()
        apache = subprocess.Popen('pkill --signal HUP --uid root httpd'.split(), stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    except ValueError:
        apache = subprocess.Popen(['httpd'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    (stdout, stderr) = apache.communicate()
    if stdout != None and len(stdout) != 0:
        sys.stderr.write("\n=== STDOUT from restart_apache():\n%s\n===\n" % stdout.rstrip())
    if stderr != None and len(stderr) != 0:
        sys.stderr.write("\n=== STDERR from restart_apache():\n%s\n===\n" % stderr.rstrip())
    subprocess.call(['sleep', '3'])


def run_command(cmd, ignore_warnings=False, wait=True, ignore_errors=False):
    """
    Runs the provided command on the terminal and prints any stderr output.
    Arguments:
        cmd -- the command to be executed.
        ignore_warnings -- if set to True, warnings
            will be ignored (defaults to False)
    """
    # print '\nRunning command: ' + cmd
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if wait:
        process.wait()
    if not ignore_warnings:
        output_err = open(cmd.split(' ')[0] + '.err', 'a')
        for error in process.stderr:
            if not ignore_warnings or "WARNING" not in error:
                print error
                output_err.write(error)
        output_err.close
    return None

def mrfgen_run_command(cmd, ignore_warnings=False, show_output=False):
    """
    Runs the provided command on the terminal and prints any stderr output.
    Arguments:
        cmd -- the command to be executed.
        ignore_warnings -- if set to True, warnings
            will be ignored (defaults to False)
    """
    # print '\nRunning command: ' + cmd
    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in process.communicate():
        if line:
            if show_output is True or 'error' in line.lower() or ignore_warnings and 'warning' in line.lower():
                print line



def find_string(file_path, string):
    try:
        with open(file_path, 'r') as f:
            result = any(line for line in f if string in line)
    except OSError:
        result = False
    return result


def search_for_strings(string_list, file_path):
    """
    Searches a given text file for a given string.
    Returns True if Found, false otherwise.
    Arguments:
        string -- a list of strings to search for.
        file_path -- the path of the file to search in.
    """
    search_result = False
    # Search each line for each item in the search list.
    # If the line is found, it's removed from the search list.
    with open(file_path, "r") as file:
        for line in file:
            line_result = next((string for string in string_list if string in line), None)
            if line_result is not None:
                string_list.remove(line_result)
    # Return True if search list has been emptied out (everything found)
    if not string_list:
        search_result = True
    return search_result


def get_file_hash(file):
    """
    Creates an MD5 hash for a given file.
    Returns True if it matches the given reference hash, False otherwise.
    Arguments:
        file -- file object to be hashed
        ref_hash -- comparison hash string
    """
    hasher = hashlib.md5()
    hasher.update(file.read())
    hash_value = hasher.hexdigest()
    return hash_value


def create_continuous_period_test_files(path, period_units, period_length, num_periods, start_datetime, prefix='',
                                        suffix='_.mrf', prototype_file=None, make_year_dirs=False, no_files=False):
    """
    Fills a directory structure with files that have a continuous period interval between them
    using the specified parameters.
    Arguments:
        path -- base directory tree to populate.
        period_units -- unit size of each period in 'days', 'months', or 'years'.
        period_length -- the length of each period in the aforementioned units.
        num_periods -- the number of period files to create.
        start_date -- a datetime.datetime object with the desired start date.
        prefix -- (optional) a string to append to the beginning of each filename.
        suffix -- (optional) a string to append to the end of each filename.
        prototype_file -- (optional) a prototype file to create each copy from (otherwise creates just empty files).
        make_year_dirs -- (optional) choose to create separate year dirs for the created files instead of dumping them all
            in one dir.
        no_files -- (optional) returns a list of dates but creates no files.
    """
    if not no_files:
        make_dir_tree(path)
    # Keep track of each date so we can evaluate if a new year directory needs to be created.
    test_dates = []
    date = start_datetime
    year_dir = ''
    # Create a set of date intervals and corresponding dummy files
    for x in range(0, num_periods + 1):
        test_dates.append(date)
        if any(unit in period_units for unit in ('hours', 'minutes', 'seconds')):
            subdaily = True
        else:
            subdaily = False

        if not no_files:
            # Create year directory if requested
            if make_year_dirs and (not x or test_dates[-1].year != date.year):
                year_dir = str(date.year)
                make_dir_tree(os.path.join(path, year_dir))

            # Assemble new filename and create file, using prototype if specified
            if subdaily is True:
                time_string = str(date.hour).zfill(2) + str(date.minute).zfill(2) + str(date.second).zfill(2)
            else:
                time_string = ''
            filename = prefix + str(date.year) + str(date.timetuple().tm_yday).zfill(3) + time_string + suffix
            output_path = os.path.join(path, year_dir)
            output_file = os.path.join(output_path, filename)
            if prototype_file:
                try:
                    copyfile(prototype_file, output_file)
                except OSError:
                    pass
            else:
                open(output_file, 'a').close()
        date += relativedelta(**{period_units: period_length})
    return test_dates


def create_intermittent_period_test_files(path, period_units, period_length, num_periods, start_datetime, prefix='',
                                          suffix='_.mrf', prototype_file=None, make_year_dirs=False, no_files=False):
    """
    Fills a directory structure with files that have an intermittent period
    using the specified parameters. Returns a list of all the date intervals
    that were created.
    Arguments:
        path -- base directory tree to populate.
        period_units -- unit size of each period in 'days', 'months', or 'years'.
        period_length -- the length of each period in the aforementioned units
        num_periods -- the number of interval pairs to create.
        start_date -- a datetime.date object with the desired start date
        prefix -- (optional) a string to append to the beginning of each filename.
        suffix -- (optional) a string to append to the end of each filename.
        prototype_file -- (optional) a prototype file to create each copy from (otherwise creates just empty files).
        make_year_dirs -- (optional) choose to create separate year dirs for the created files instead of dumping them all
            in one dir.
        no_files -- (optional) returns a list of dates but creates no files.
    """
    if not no_files:
        make_dir_tree(path)
    # Create a list of date intervals, each separated by the specified period length
    test_dates = []
    year_dir = ''
    for x in range(num_periods):
        # Create a new start date and end date for each interval requested
        interval_set = []
        for y in range(1, 5):
            date = start_datetime + relativedelta(**{period_units: period_length * y})
            interval_set.append(date)
        test_dates.append(interval_set)

        # Push the start time of the next interval to twice the period distance from the end of the last interval
        start_datetime = interval_set[-1] + relativedelta(**{period_units: period_length * 2})

        if not no_files:
            if any(unit in period_units for unit in ('hours', 'minutes', 'seconds')):
                subdaily = True
            else:
                subdaily = False

            # If this is the first date or it has a different year than the previous, create that dir
            if make_year_dirs and (not x or test_dates[-1][-1].year != date.year):
                year_dir = str(date.year)
                make_dir_tree(os.path.join(path, year_dir))
            for interval in interval_set:
                if subdaily is True:
                    time_string = str(interval.hour).zfill(2) + str(interval.minute).zfill(2) + str(interval.second).zfill(2)
                else:
                    time_string = ''
                filename = prefix + str(interval.year) + str(interval.timetuple().tm_yday).zfill(3) + time_string + suffix
                output_path = os.path.join(path, year_dir)
                output_file = os.path.join(output_path, filename)

                if prototype_file:
                    try:
                        copyfile(prototype_file, output_file)
                    except OSError:
                        pass
                else:
                    open(output_file, 'a').close()
    return test_dates


def read_zkey(zdb, sort):
    """
    Reads z-index database file and returns the first or last key depending on sort order
    Arguments:
        zdb -- the z-index database file name
        sort -- the sort order
    """
    try:
        db_exists = os.path.isfile(zdb)
        if db_exists is False:
            return None
        else:
            con = sqlite3.connect(zdb, timeout=60)  # 1 minute timeout
            cur = con.cursor()

            # Check for existing key
            cur.execute("SELECT key_str FROM ZINDEX ORDER BY key_str " + sort + " LIMIT 1;")
            try:
                key = cur.fetchone()[0]
            except:
                return None
            if con:
                con.close()
            return key

    except sqlite3.Error, e:
        if con:
            con.rollback()
        mssg = "%s:" % e.args[0]
        print mssg
        return None


def get_file_list(path):
    files = []
    for name in os.listdir(path):
        filepath = os.path.join(path, name)
        if os.path.isfile(filepath):
            file.append(filepath)
    return files


def get_layer_config(filepath, archive_config):
    """
    Parses a layer config XML file and its associated environment config file
    and returns a dict with relevant values. Generally, <TagName> turns into config['tag_name'].
    Arguments:
        filepath -- path to the layer config file
        archive config -- path to the archive config file
    """
    config = {}

    # Get the layer, environment, and archive config DOMs
    try:
        with open(filepath, "r") as lc:
            config_dom = xml.dom.minidom.parse(lc)
            env_config = config_dom.getElementsByTagName("EnvironmentConfig")[0].firstChild.nodeValue
    except IOError:
        print "Cannot read file " + filepath
        return config
    try:
        with open(archive_config, "r") as archive:
            archive_dom = xml.dom.minidom.parse(archive)
    except IOError:
        print "Cannot read file " + archive_config
        return config 

    # Get archive root path and the archive location
    archive_root = config_dom.getElementsByTagName('ArchiveLocation')[0].attributes['root'].value
    config['archive_basepath'] = next(loc.getElementsByTagName('Location')[0].firstChild.nodeValue for loc in archive_dom.getElementsByTagName('Archive') if loc.attributes['id'].value == archive_root)
    config['archive_location'] = os.path.join(config['archive_basepath'], config_dom.getElementsByTagName('ArchiveLocation')[0].firstChild.nodeValue)

    # Add everything we need from the layer config
    config['prefix'] = config_dom.getElementsByTagName("FileNamePrefix")[0].firstChild.nodeValue
    config['identifier'] = config_dom.getElementsByTagName("Identifier")[0].firstChild.nodeValue
    config['time'] = config_dom.getElementsByTagName("Time")[0].firstChild.nodeValue
    config['tiled_group_name'] = config_dom.getElementsByTagName("TiledGroupName")[0].firstChild.nodeValue
    config['colormaps'] = config_dom.getElementsByTagName("ColorMap")
    try:
        config['empty_tile'] = config_dom.getElementsByTagName('EmptyTile')[0].firstChild.nodeValue
    except IndexError:
        config['empty_tile_size'] = config_dom.getElementsByTagName('EmptyTileSize')[0].firstChild.nodeValue
    config['year_dir'] = False
    try:
        if config_dom.getElementsByTagName('ArchiveLocation')[0].attributes['year'].value == 'true':
            config['year_dir'] = True
    except KeyError:
        pass
    try:
        config['vector_type'] = config_dom.getElementsByTagName('VectorType')[0].firstChild.nodeValue
        config['vector_style_file'] = config_dom.getElementsByTagName('VectorStyleFile')[0].firstChild.nodeValue
    except IndexError:
        pass
    
    try:
        with open(env_config, "r") as env:
            env_dom = xml.dom.minidom.parse(env)
    except IOError:
        print "Cannot read file " + env_config
        return config
    # Add everything we need from the environment config
    staging_locations = env_dom.getElementsByTagName('StagingLocation')
    config['wmts_staging_location'] = next((loc.firstChild.nodeValue for loc in staging_locations if loc.attributes["service"].value == "wmts"), None)
    config['twms_staging_location'] = next((loc.firstChild.nodeValue for loc in staging_locations if loc.attributes["service"].value == "twms"), None)
    config['cache_location'] = next((loc.firstChild.nodeValue for loc in env_dom.getElementsByTagName("CacheLocation") if loc.attributes["service"].value == "wmts"), None)
    config['wmts_gc_path'] = next((loc.firstChild.nodeValue for loc in env_dom.getElementsByTagName("GetCapabilitiesLocation") if loc.attributes["service"].value == "wmts"), None)
    config['twms_gc_path'] = next((loc.firstChild.nodeValue for loc in env_dom.getElementsByTagName("GetCapabilitiesLocation") if loc.attributes["service"].value == "twms"), None)
    config['colormap_locations'] = [loc for loc in env_dom.getElementsByTagName("ColorMapLocation")]
    config['legend_location'] = env_dom.getElementsByTagName('LegendLocation')[0].firstChild.nodeValue
    try:
        config['mapfile_location'] = env_dom.getElementsByTagName('MapfileLocation')[0].firstChild.nodeValue
        config['mapfile_location_basename'] = env_dom.getElementsByTagName('MapfileLocation')[0].attributes["basename"].value
        config['mapfile_staging_location'] = env_dom.getElementsByTagName('MapfileStagingLocation')[0].firstChild.nodeValue
    except (IndexError, KeyError):
        pass

    return config


def get_time_string(start_datetime, end_datetime, config):
    """
    Returns a GetCapabilities date search string for the given start and end datetimes.
    """
    # Use those dates to create the search string we're looking for in the GC file
    time_string = start_datetime.isoformat() + 'Z/' + end_datetime.isoformat() + 'Z'

    # Check if a period length is added to the 'Time' tag.
    detect_string = config['time'].split('/')
    if detect_string[0].startswith('P'):
        time_string = detect_string[0] + time_string + '/'
    elif detect_string[-1].startswith('P'):
        time_string += ('/' + detect_string[-1])

    return time_string


def make_dir_tree(path, ignore_existing=False):
    """
    Creates the specified directory tree. Throws an error
    and doesn't do anything if there are already files in that dir.
    Kind of like 'mkdir -p'.
    Arguments:
        path -- path to be created
    """
    try:
        os.makedirs(path)
    except OSError:
        if os.listdir(path):
            if not ignore_existing:
                raise OSError("Target directory {0} is not empty.".format(path))
            else:
                pass
        else:
            pass
    return


def setup_test_layer(test_file_path, cache_path, prefix):
    """
    Sets up a test imagery layer by copying the data files and the cache config file
    to the specified directories. It also restarts Apache in order for these changes to take effect.
    Arguments:
        test_file_path -- the path of the dir where the test files are located.
        cache_path -- the path of the dir where the cache files are located
        prefix -- the prefix of the data and cache files that will be copied.
    """
    make_dir_tree(os.path.join(cache_path, prefix))

    # Copy MRF files to a new cache directory and the cache file to the root of the cache location
    for file in os.listdir(test_file_path):
        if os.path.isfile(os.path.join(test_file_path, file)) and prefix in file:
            if any(ext for ext in ('.mrf', 'ppg', 'idx', '.pjg') if ext in file):
                copy(os.path.join(test_file_path, file), cache_path)
            elif '_cache.config' in file:
                copy(os.path.join(test_file_path, file), os.path.join(cache_path, 'cache_all_wmts.config'))

    run_command('apachectl stop')
    run_command('apachectl start')
    return


def get_url(url):
    """
    Grabs and returns a file from a url.
    Arguments
        url -- the URL of the file to be downloaded.
    """
    try:
        response = urllib2.urlopen(url)
    except urllib2.URLError:
        raise urllib2.URLError('Cannot access URL: ' + url)
    return response


def check_apache_running():
    """
    Checks to see if Apache is running on the test machine, bails if it's not.
    """
    # Greps for any running HTTPD processes
    check = subprocess.Popen('ps -e | grep "httpd"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if not check.stdout.read():
        raise ValueError('Apache does not appear to be running.')
    return True


def ordered_d(obj): 
    """
    Recursively sort any lists it finds (and convert dictionaries to lists of (key, value) pairs 
    """
    if isinstance(obj, dict):
        return sorted((k, ordered_d(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered_d(x) for x in obj)
    else:
        return obj


def check_dicts(d, ref_d):
    """
    Checks to see if dict d is equivalent to dict ref_d.
    Arguments:
        d -- dict to compare
        ref_d -- reference dict being compared against
    """
    if ordered_d(ref_d) == ordered_d(d) :
        return True
    else:
        return False


def check_tile_request(url, ref_hash):
    """
    Checks to see if Apache is running, downloads a tile from the specified URL,
    and checks it against a hash value. Returns true or false.
    Arguments
        url -- the URL of the tile to be tested
        ref_hash -- the hash that the file will be tested against.
    """
    check_apache_running()
    tile = get_url(url)
    hash_check = get_file_hash(tile) == ref_hash
    return hash_check


def check_response_code(url, code, code_value=''):
    """
    Checks the response code and optional code value returned from OnEarth against given criteria.
    Arguments:
        url -- URL to be requested.
        code -- integer HTTP reponse code
        code_value -- any text that should appear in the response from OnEarth
    """
    check_apache_running()
    try:
        response = urllib2.urlopen(url)
        r_code = 200
    except urllib2.HTTPError as e:
        r_code = e.code
        response = e
    if r_code == code and code_value in response.read():
        return True
    return False


def test_snap_request(hash_table, req_url):
    """
    Requests the first tile for a given layer and date, then compares the result against a dict w/ dates
    and hashes.
    Arguments:
        hash_table -- a dict with date keys and hash values.
        req_url -- a string with the url that's to be used for the request
    """
    tile = get_url(req_url)
    tile_hash = get_file_hash(tile)

    # Get the date that the particular hash is associated with
    tile_date = hash_table.get(tile_hash, '')
    return tile_date


def get_xml(file):
    """
    Opens an XML file, parses it, and returns a DOM object.
    Returns 'None' if not valid XML.
    Arguments:
        file -- file to be opened.
    """
    with open(file, 'r') as f:
        try:
            dom = xml.dom.minidom.parse(f)
        except xml.parsers.expat.ExpatError:
            return None
    return dom


def file_text_replace(infile, outfile, before, after):
    """
    Replaces text in given file and saves the output to the
    location specified.
    Arguments:
        infile -- input file path
        outfile -- path of new file to be saved (deletes existing)
        before -- string to search for
        after -- string to replace 'before' with
    """
    with open(infile, 'r') as template:
        newfile = template.read().replace(before, after)
        with open(outfile, 'w') as out:
            out.write(newfile)


def check_valid_mvt(file, warn_if_empty=False):
    tile_buffer = StringIO.StringIO()
    tile_buffer.write(file.read())
    tile_buffer.seek(0)
    try:
        unzipped_tile = gzip.GzipFile(fileobj=tile_buffer)
        tile_data = unzipped_tile.read()
    except IOError:
        return False
    try:
        tile = mapbox_vector_tile.decode(tile_data)
    except:
        return False
    if warn_if_empty:
        try:
            num_features = len(tile[tile.keys()[0]]['features'])
        except IndexError:
            return False
    return True


def test_wmts_error(test_obj, test_url, error_code_expected, exception_code_expected, locator_expected, exception_text_expected):
    r = requests.get(test_url)
    test_obj.assertEqual(error_code_expected, r.status_code, msg='Unexpected error code -- should be {0}, is {1}'.format(error_code_expected, str(r.status_code)))
    content_type = r.headers.get('content-type')
    test_obj.assertEqual('text/xml', content_type, msg='Unexpected content type, should be {0}, is {1}'.format('text/xml', content_type))
    try:
        err_xml = etree.fromstring(r.content)
    except etree.XMLSyntaxError:
        test_obj.fail('Invalid XML returned for error message')

    # Check root element attributes
    expected_namespace = '{http://www.opengis.net/ows/1.1}'
    root_element_expected_value = expected_namespace + 'ExceptionReport'
    test_obj.assertEqual(root_element_expected_value, err_xml.tag, msg='Invalid root element or namespace, should be {0}, is {1}'.format(root_element_expected_value, err_xml.tag))

    schema_location_found = err_xml.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
    test_obj.assertIsNotNone(schema_location_found, msg='Missing schemaLocation attribute from ExceptionReport element')
    schema_location_expected = 'http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd'
    test_obj.assertEqual(schema_location_expected, schema_location_found, msg='Invalid schemaLocation attribute for ExceptionReport element, should be {0}, is {1}'.format(schema_location_expected, schema_location_found))

    version_found = err_xml.attrib.get('version')
    test_obj.assertIsNotNone(version_found, msg='Missing version attribute for ExceptionReport element')
    version_expected = '1.1.0'
    test_obj.assertEqual(version_expected, version_found, msg='Invalid version attribute for ExceptionReport element, should be {0}, is {1}'.format(version_expected, version_found))

    lang_found = err_xml.attrib.get('{http://www.w3.org/XML/1998/namespace}lang')
    test_obj.assertIsNotNone(lang_found, msg='Missing xml:lang attribute from ExceptionReport element')
    lang_expected = 'en'
    test_obj.assertEqual(lang_expected, lang_found, msg='Invalid xml:lang attribute for ExceptionReport element, should be {0}, is {1}'.format(lang_expected, lang_found))

    # Check <Exception> content
    exception_element = err_xml.find(expected_namespace + 'Exception')
    test_obj.assertIsNotNone(exception_element, msg='Missing Exception element')

    exception_code_found = exception_element.attrib.get('exceptionCode')
    test_obj.assertIsNotNone(exception_code_found, msg='Mising exceptionCode attribute for Exception element')
    test_obj.assertEqual(exception_code_expected, exception_code_found, msg='Invalid exceptionCode attribute for Exception element, should be {0}, is {1}'.format(exception_code_expected, exception_code_found))

    locator_found = exception_element.attrib.get('locator')
    test_obj.assertIsNotNone(locator_found, msg='Mising locator attribute for Exception element')
    # locator_expected = 'LAYER'
    test_obj.assertEqual(locator_expected, locator_found, msg='Invalid locator attribute for Exception element, should be {0}, is {1}'.format(locator_expected, locator_found))

    # Check <ExceptionText> content
    exception_text_element = exception_element.find(expected_namespace + 'ExceptionText')
    test_obj.assertIsNotNone(exception_text_element, msg='Missing ExceptionText element')

    exception_text_found = exception_text_element.text
    test_obj.assertIsNotNone(exception_text_found, msg='Missing ExceptionText text content')
    test_obj.assertEqual(exception_text_expected, exception_text_found, msg='Invalid text content for ExceptionText element, should be {0}, is {1}'.format(exception_text_expected, exception_text_found))
