#!/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# oe_configure_remote_layers.py
# OnEarth Remote Layers Configurator

# Example remote XML configuration file:

'''
<RemoteGetCapabilities>
    <SrcWMTSGetCapabilitiesURI>https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml</SrcWMTSGetCapabilitiesURI>
    <SrcTWMSGetCapabilitiesURI>https://gibs.earthdata.nasa.gov/twms/epsg4326/best/twms.cgi?request=GetCapabilities</SrcTWMSGetCapabilitiesURI>
    <SrcTWMSGetTileServiceURI>https://gibs.earthdata.nasa.gov/twms/epsg4326/best/twms.cgi?request=GetTileService</SrcTWMSGetTileServiceURI>
    <SrcLocationRewrite internal="https://gibs.earthdata.nasa.gov" external="https://gitc.earthdata.nasa.gov" />
    <EnvironmentConfig>/etc/onearth/config/conf/environment_geographic.xml</EnvironmentConfig>
    <IncludeLayer>Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual</IncludeLayer>
    <ExcludeLayer>BlueMarble_NextGeneration</ExcludeLayer>
</RemoteGetCapabilities>
'''

import os
import sys
import requests
import xml.dom.minidom
import logging
import cgi
from lxml import etree
from time import asctime
from optparse import OptionParser
from oe_utils import get_environment, sigevent, get_dom_tag_value, bulk_replace
from oe_configure_reproject_layer import get_max_scale_dem, get_epsg_code_for_proj_string, get_bbox_for_proj_string, make_gdal_tms_xml, \
    MAPFILE_TEMPLATE, WMS_LAYER_GROUP_TEMPLATE, DIMENSION_TEMPLATE, STYLE_TEMPLATE, VALIDATION_TEMPLATE


VERSION_NUMBER = '1.3.8'
LAYER_NODE = '<Layer xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml">'
LAYER = '      <Layer>'
warnings = []
errors = []


def log_sig_warn(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.warning(asctime() + " " + mssg)
    global warnings
    warnings.append(asctime() + " " + mssg)
    # Send to sigevent.
    try:
        sigevent('WARN', mssg, sigevent_url)
    except Exception:
        print 'sigevent service is unavailable'


def log_sig_err(mssg, sigevent_url):
    """
    Send a warning to the log and to sigevent.
    Arguments:
        mssg -- 'message for operations'
        sigevent_url -- Example:  'http://[host]/sigevent/events/create'
    """
    # Send to log.
    logging.error(asctime() + " " + mssg)
    global errors
    errors.append(asctime() + " " + mssg)
    # Send to sigevent.
    try:
        sigevent('ERROR', mssg, sigevent_url)
    except Exception:
        print 'sigevent service is unavailable'


def get_remote_layers(conf, wmts=True, twms=True, sigevent_url=None, debug=False, create_mapfile=False):
    '''
    Add layers from remote GetCapabilities if config found
    '''
    print('\nReading remote layers config file ' + conf)
    dom = xml.dom.minidom.parse(conf)
    # Get environment
    try:
        environmentConfig = get_dom_tag_value(dom, 'EnvironmentConfig')
        try:
            environment = get_environment(environmentConfig,
                                          '' if sigevent_url is None else sigevent_url)
        except Exception, e:
            log_sig_err(str(e), sigevent_url)
    except IndexError:
        mssg = 'Required <EnvironmentConfig> element is missing in ' + conf
        log_sig_err(mssg, sigevent_url)

    # Get default email server and recipient if not override
    if sigevent_url is None:
        email_server = environment.emailServer
        email_recipient = environment.emailRecipient
        email_sender = environment.emailSender
        sigevent_url = (email_server, email_recipient, email_sender)
        if email_recipient == '':
            mssg = 'No email recipient provided for notifications in get_remote_layers.'
            log_sig_err(mssg, sigevent_url)
            
    # Check to see if we want to rewrite locations
    try:
        srcLocationRewrite = dom.getElementsByTagName('SrcLocationRewrite')[0]
        try:
            internal_location = srcLocationRewrite.getAttribute('internal')
            external_location = srcLocationRewrite.getAttribute('external')
            print('SrcLocationRewrite internal={} external={}\n'.format(internal_location, external_location))
        except Exception, e:
            log_sig_err(str(e), sigevent_url)
    except IndexError:
        srcLocationRewrite = None
        print('Not using SrcLocationRewrite\n')

    # Get layers to include or exclude
    include_layers  = []
    wms_group_names = {}
    for tag in dom.getElementsByTagName('IncludeLayer'):
        identifier = tag.firstChild.data.strip()
        include_layers.append(identifier)
        try:
            wms_group_names[identifier] = str(tag.attributes['WMSLayerGroupName'].value).strip()
        except:
            wms_group_names[identifier] = None

    print('Including layers:')
    print('\n'.join(include_layers))

    exclude_layers = [tag.firstChild.data.strip() for tag in dom.getElementsByTagName('ExcludeLayer')]
    print('Excluding layers:')
    print('\n'.join(exclude_layers))

    if(wmts):
        try:
            wmts_getcapabilities = get_dom_tag_value(dom, 'SrcWMTSGetCapabilitiesURI')
        except IndexError:
            mssg = 'SrcWMTSGetCapabilitiesURI element is missing in ' + conf
            log_sig_err(mssg, sigevent_url)
        # Download and parse GetCapabilites XML
        try:
            print('\nLoading layers from ' + wmts_getcapabilities)
            r = requests.get(wmts_getcapabilities)
            if r.status_code != 200:
                log_sig_err('Can\'t download WMTS GetCapabilities from URL: ' +
                            wmts_getcapabilities, sigevent_url)
        except Exception:
            log_sig_err('Can\'t download WMTS GetCapabilities from URL: ' +
                        wmts_getcapabilities, sigevent_url)
        # Get the layers from the source GC file
        try:
            gc_xml = etree.fromstring(r.content)
            ows = '{' + gc_xml.nsmap['ows'] + '}'
            gc_layers = gc_xml.find('{*}Contents').findall('{*}Layer')
            for layer in gc_layers:
                if(debug):
                    print(etree.tostring(layer))
                identifier = layer.findtext(ows + 'Identifier')

                if (len(include_layers) > 0 and identifier not in include_layers) or (identifier in exclude_layers):
                    if debug:
                        print 'Skipping layer: ' + identifier
                    continue

                xml_filename = os.path.join(environment.wmts_dir,
                                            identifier + '_remote_.xml')
                print('Creating XML file: ' + xml_filename)
                with open(xml_filename, 'w+') as xml_file:
                    xml_string = etree.tostring(layer).replace(LAYER_NODE, LAYER)
                    if(srcLocationRewrite is not None):
                        xml_string = xml_string.replace(external_location, internal_location)
                    xml_file.write(xml_string)
        except etree.XMLSyntaxError:
            log_sig_err('Can\'t parse WMTS GetCapabilities file (invalid syntax): ' +
                        wmts_getcapabilities, sigevent_url)
    else:
        print('\nSkipping WMTS')

    if(twms):
        # TWMS GetCapabilities
        try:
            twms_getcapabilities = get_dom_tag_value(dom, 'SrcTWMSGetCapabilitiesURI')
        except IndexError:
            mssg = 'SrcTWMSGetCapabilitiesURI element is missing in ' + conf
            log_sig_err(mssg, sigevent_url)
        # Download and parse GetCapabilites XML
        try:
            print('\nLoading layers from ' + twms_getcapabilities)
            r = requests.get(twms_getcapabilities)
            if r.status_code != 200:
                log_sig_err('Can\'t download TWMS GetCapabilities from URL: ' +
                            twms_getcapabilities, sigevent_url)
        except Exception:
            log_sig_err('Can\'t download TWMS GetCapabilities from URL: ' +
                        twms_getcapabilities, sigevent_url)
        # Get the layers from the source GC file
        try:
            twms_gc_xml = etree.fromstring(r.content)
            twms_gc_layers = twms_gc_xml.find('{*}Capability').findall('{*}Layer')[0].findall('{*}Layer')
            for layer in twms_gc_layers:
                if(debug):
                    print(etree.tostring(layer))
                identifier = layer.findtext('Abstract').replace(' abstract', '')

                if (len(include_layers) > 0 and identifier not in include_layers) or (identifier in exclude_layers):
                    if debug:
                        print 'Skipping layer: ' + identifier
                    continue

                xml_filename = os.path.join(environment.twms_dir,
                                            identifier + '_remote__gc.xml')
                print('Creating XML file: ' + xml_filename)
                with open(xml_filename, 'w+') as xml_file:
                    xml_string = etree.tostring(layer)
                    if(srcLocationRewrite is not None):
                        xml_string = xml_string.replace(external_location, internal_location)
                    xml_file.write(xml_string)
        except etree.XMLSyntaxError:
            log_sig_err('Can\'t parse TWMS GetCapabilities file (invalid syntax): ' +
                        twms_getcapabilities, sigevent_url)
        # TWMS GetTileService
        try:
            twms_gettileservice = get_dom_tag_value(dom, 'SrcTWMSGetTileServiceURI') 
        except IndexError:
            mssg = 'SrcTWMSGetTileServiceURI element is missing in ' + conf
            log_sig_err(mssg, sigevent_url)
        # Download and parse GetTileService XML
        try:
            print('\nLoading layers from ' + twms_gettileservice)
            r = requests.get(twms_gettileservice)
            if r.status_code != 200:
                log_sig_err('Can\'t download TWMS GetTileService from URL: ' +
                            twms_gettileservice, sigevent_url)
        except Exception:
            log_sig_err('Can\'t download TWMS GetTileService from URL: ' +
                        twms_gettileservice, sigevent_url)
        # Get the layers from the source GTS file
        try:
            twms_gts_xml = etree.fromstring(r.content)
            twms_gts_tiledgroup = twms_gts_xml.find('{*}TiledPatterns').findall('{*}TiledGroup')
            for tiledgroup in twms_gts_tiledgroup:
                if(debug):
                    print(etree.tostring(tiledgroup))
                identifier = tiledgroup.findtext('Abstract').replace(' abstract', '')

                if (len(include_layers) > 0 and identifier not in include_layers) or (identifier in exclude_layers):
                    if debug:
                        print 'Skipping layer: ' + identifier
                    continue

                xml_filename = os.path.join(environment.twms_dir,
                                            identifier + '_remote__gts.xml')
                print('Creating XML file: ' + xml_filename)
                with open(xml_filename, 'w+') as xml_file:
                    xml_string = etree.tostring(tiledgroup)
                    if(srcLocationRewrite is not None):
                        xml_string = xml_string.replace(external_location, internal_location)
                    xml_file.write(xml_string)
        except etree.XMLSyntaxError:
            log_sig_err('Can\'t parse TWMS GetTileService file (invalid syntax): ' +
                        twms_getcapabilities, sigevent_url)
    else:
        print('\nSkipping TWMS')


    if create_mapfile:
        # Check for all required config info
        try:
            environment_xml = etree.parse(environmentConfig)
        except IOError:
            log_sig_err("Can't open environment config file: {0}".format(
                environmentConfig), sigevent_url)
        except etree.XMLSyntaxError:
            log_sig_err("Can't parse environment config file: {0}".format(
                environmentConfig), sigevent_url)
        
        mapfile_location = environment_xml.findtext('{*}MapfileLocation')
        if not mapfile_location:
            mssg = 'mapfile creation chosen but no <MapfileLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_location_basename = environment_xml.find(
            '{*}MapfileConfigLocation').get('basename')
        if not mapfile_location_basename:
            mssg = 'mapfile creation chosen but no "basename" attribute found for <MapfileLocation>'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_staging_location = environment_xml.findtext(
            '{*}MapfileStagingLocation')
        if not mapfile_staging_location:
            mssg = 'mapfile creation chosen but no <MapfileStagingLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_config_location = environment_xml.findtext(
            '{*}MapfileConfigLocation')
        if not mapfile_config_location:
            mssg = 'mapfile creation chosen but no <MapfileConfigLocation> found'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)

        mapfile_config_basename = environment_xml.find(
            '{*}MapfileConfigLocation').get('basename')
        if not mapfile_config_basename:
            mssg = 'mapfile creation chosen but no "basename" attribute found for <MapfileConfigLocation>'
            warnings.append(asctime() + " " + mssg)
            log_sig_warn(mssg, sigevent_url)
            
        try:
            wmts_getcapabilities = get_dom_tag_value(dom, 'SrcWMTSGetCapabilitiesURI')
        except IndexError:
            mssg = 'SrcWMTSGetCapabilitiesURI element is missing in ' + conf
            log_sig_err(mssg, sigevent_url)
        # Download and parse GetCapabilites XML
        try:
            print('\nLoading layers from ' + wmts_getcapabilities)
            r = requests.get(wmts_getcapabilities)
            if r.status_code != 200:
                log_sig_err('Can\'t download WMTS GetCapabilities from URL: ' +
                            wmts_getcapabilities, sigevent_url)
        except Exception:
            log_sig_err('Can\'t download WMTS GetCapabilities from URL: ' +
                        wmts_getcapabilities, sigevent_url)
        # Get the layers from the source GC file
        try:
            gc_xml = etree.fromstring(r.content)
            tilematrixsets = gc_xml.find('{*}Contents').findall('{*}TileMatrixSet')
            ows = '{' + gc_xml.nsmap['ows'] + '}'
            xlink = '{http://www.w3.org/1999/xlink}'
            gc_layers = gc_xml.find('{*}Contents').findall('{*}Layer')
            for layer in gc_layers:
                if(debug):
                    print(etree.tostring(layer))
                identifier = layer.findtext(ows + 'Identifier')
                if (len(include_layers) > 0 and identifier not in include_layers) or (identifier in exclude_layers):
                    if debug:
                        print 'Skipping layer: ' + identifier
                    continue

                dest_dim_elem = layer.find('{*}Dimension')
                if dest_dim_elem is not None and dest_dim_elem.findtext(ows + 'Identifier') == 'Time':
                    static = False
                src_format = layer.findtext('{*}Format')
                src_title = layer.findtext(ows + 'Title')
        
                # Get TMSs for this layer and build a config for each
                tms_list = [elem for elem in tilematrixsets if elem.findtext(
                    ows + 'Identifier') == layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')]
                layer_tilematrixsets = sorted(tms_list, key=get_max_scale_dem)
        
                #HACK
                if len(layer_tilematrixsets) == 0:
                    print("No layer_tilematrixsets. Skipping layer: " + identifier)
                    continue

                # Use the template to create the new Mapfile snippet
                wms_layer_group_info = ''
                dimension_info = ''
                validation_info = ''
                style_info = ''

                if wms_group_names[identifier] is not None:
                    wms_layer_group_info = bulk_replace(WMS_LAYER_GROUP_TEMPLATE,
                                                        [('{wms_layer_group}', wms_group_names[identifier])])

                if not static:
                    default_datetime = dest_dim_elem.findtext('{*}Default')
                    period_str = ','.join(
                        elem.text for elem in dest_dim_elem.findall("{*}Value"))
                    dimension_info = bulk_replace(DIMENSION_TEMPLATE, [('{periods}', period_str),
                                                                       ('{default}', default_datetime)])
                    validation_info = VALIDATION_TEMPLATE.replace(
                        '{default}', default_datetime)
                
                # If the source EPSG:4326 layer has a legend, then add that to the EPSG:3857 layer also
                legendUrlElems = []
                
                for styleElem in layer.findall('{*}Style'):
                    legendUrlElems.extend(styleElem.findall('{*}LegendURL'))
                
                for legendUrlElem in legendUrlElems:
                    attributes = legendUrlElem.attrib
                    if attributes[xlink + 'role'].endswith("horizontal"):
                        style_info = bulk_replace(STYLE_TEMPLATE, [('{width}', attributes["width"]),
                                                                   ('{height}', attributes["height"]),
                                                                   ('{href}', attributes[xlink + 'href'].replace(".svg",".png"))])
                
                # Mapserver automatically converts to RGBA and works better if we
                # specify that for png layers
                mapserver_bands = 4 if 'image/png' in src_format else 3
                
                src_crs = layer_tilematrixsets[0].findtext('{*}SupportedCRS')
                src_epsg = get_epsg_code_for_proj_string(src_crs)
                
                target_bbox = map(
                    str, get_bbox_for_proj_string('EPSG:' + src_epsg, get_in_map_units=(src_epsg not in ['4326','3413','3031'])))
                target_bbox = [target_bbox[1], target_bbox[0], target_bbox[3], target_bbox[2]]

                mapfile_snippet = bulk_replace(
                    MAPFILE_TEMPLATE, [('{layer_name}', identifier), ('{data_xml}', make_gdal_tms_xml(layer, mapserver_bands, src_epsg)), ('{layer_title}', cgi.escape(src_title)),
                                       ('{wms_layer_group_info}', wms_layer_group_info), ('{dimension_info}', dimension_info), ('{style_info}', style_info), ('{validation_info}', validation_info),
                                       ('{src_epsg}', src_epsg), ('{target_epsg}', src_epsg), ('{target_bbox}', ', '.join(target_bbox))])

                mapfile_name = os.path.join(
                    mapfile_staging_location, identifier + '.map')
                with open(mapfile_name, 'w+') as f:
                    f.write(mapfile_snippet)

        except etree.XMLSyntaxError:
            log_sig_err('Can\'t parse WMTS GetCapabilities file (invalid syntax): ' +
                        wmts_getcapabilities, sigevent_url)
            
        

    return (warnings, errors)


if __name__ == '__main__':
    print('OnEarth Remote Layers Configurator')
    usageText = 'oe_configure_remote_layers.py --conf_file [remote_getcapabilities.xml] --no_twms --no_wmts'

    # Define command line options and args.
    parser = OptionParser(usage=usageText, version=VERSION_NUMBER)
    parser.add_option('-c', '--conf_file',
                      action='store', type='string', dest='config',
                      help='Full path of layer configuration filename.')
    parser.add_option("-n", "--no_twms",
                      action="store_true", dest="no_twms",
                      default=False, help="Do not use configurations for Tiled-WMS")
    parser.add_option("-s", "--send_email", action="store_true", dest="send_email",
                      default=False, help="Send email notification for errors and warnings.")
    parser.add_option('--email_server', action='store', type='string', dest='email_server',
                      default='', help='The server where email is sent from (overrides configuration file value')
    parser.add_option('--email_recipient', action='store', type='string', dest='email_recipient',
                      default='', help='The recipient address for email notifications (overrides configuration file value')
    parser.add_option('--email_sender', action='store', type='string', dest='email_sender',
                      default='', help='The sender for email notifications (overrides configuration file value')
    parser.add_option("-w", "--no_wmts",
                      action="store_true", dest="no_wmts",
                      default=False, help="Do not use configurations for WMTS.")
    parser.add_option("--debug",
                      action="store_true", dest="debug",
                      default=False, help="Produce verbose debug messages")
    parser.add_option("--create_mapfile", dest="create_mapfile",
                      default=False, action="store_true", 
                      help="Create MapServer configuration.")

    # Read command line args.
    (options, args) = parser.parse_args()
    # No Tiled-WMS configuration.
    twms = not options.no_twms
    # No WMTS configuration.
    wmts = not options.no_wmts

    config = options.config
    if not config:
        print('No layer config XML specified')
        sys.exit()

    # Send email.
    send_email = options.send_email
    # Email server.
    email_server = options.email_server
    # Email recipient
    email_recipient = options.email_recipient
    # Email sender
    email_sender = options.email_sender
    # Email metadata replaces sigevent_url
    if send_email:
        sigevent_url = (email_server, email_recipient, email_sender)
    else:
        sigevent_url = None

    warnings, errors = get_remote_layers(config,
                                         wmts=wmts,
                                         twms=twms,
                                         sigevent_url=sigevent_url,
                                         debug=options.debug,
                                         create_mapfile=options.create_mapfile)
    mssg = '\nOnEarth Remote Layers Configurator has completed'
    if(len(warnings) > 0):
        mssg = mssg + '\nWarnings:\n' + '\n'.join(warnings)
    if(len(errors) > 0):
        mssg = mssg + '\nErrors:\n' + '\n'.join(errors)
    print(mssg)
    if sigevent_url is not None:
        sigevent('INFO', asctime() + ' ' + mssg, sigevent_url)
