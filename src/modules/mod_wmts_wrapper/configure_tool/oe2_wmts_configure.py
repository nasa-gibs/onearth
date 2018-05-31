import os
import re
import sys
import argparse
import yaml
from pathlib import Path
from urllib.parse import urlparse

# Config templates

LOCAL_DATE_SERVICE_URI = '/oe2-date-service'

MAIN_APACHE_CONFIG_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !wmts_wrapper_module>
        LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<IfModule !receive_module>
        LoadModule receive_module modules/mod_receive.so
</IfModule>

<Directory {endpoint_path}>
        WMTSWrapperRole root
</Directory>
"""

TWMS_MODULE_TEMPLATE = """<IfModule !twms_module>
    LoadModule twms_module modules/mod_twms.so
</IfModule>
"""

PROXY_MODULE_TEMPLATE = """<IfModule !proxy_module>
    LoadModule proxy_module modules/mod_proxy.so
</IfModule>
"""

DATE_SERVICE_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_date_service_uri} {date_service_uri}
ProxyPassReverse {local_date_service_uri} {date_service_uri}
"""

DATA_FILE_PROXY_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_data_file_uri} {data_file_uri}
ProxyPassReverse {local_data_file_uri} {data_file_uri}
"""

LAYER_APACHE_CONFIG_TEMPLATE = """<Directory {endpoint_path}/{layer_id}>
    WMTSWrapperRole layer
</Directory>

<Directory {endpoint_path}/{layer_id}/default>
        WMTSWrapperRole style
        WMTSWrapperEnableTime {time_enabled}
</Directory>

<Directory {endpoint_path}/{layer_id}/default/{tilematrixset}>
        MRF On
        MRF_ConfigurationFile {config_file_path}
        MRF_RegExp {alias}
        WMTSWrapperRole tilematrixset
        WMTSWrapperEnableYearDir {year_dir}
        WMTSWrapperLayerAlias {alias}
</Directory>
"""

MOD_TWMS_CONFIG_TEMPLATE = """<Directory {endpoint_path}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {endpoint_path}/twms/${layer}/twms.config
</Directory>
"""

LAYER_MOD_MRF_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
IndexFile {idx_path}"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
BoundingBox {bbox}
SourcePath {source_path}
SourcePostfix {source_postfix}
"""

MIME_TO_EXTENSION = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tiff',
    'image/lerc': '.lerc',
    'application/x-protobuf;type=mapbox-vector': '.pbf',
    'application/vnd.mapbox-vector-tile': '.mvt'
}

# Utility functions


def generate_string_from_set(sep, string_set):
    strings = []
    for pair in string_set:
        if pair[1]:
            strings.append(pair[0])
    return sep.join(strings)


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str

# Main configuration functions


def make_apache_config(endpoint_config, layer_configs):
    # Only set up the date service proxy if there are non-static layers
    date_service_needed = any(not layer_config['static']
                              for layer_config in layer_configs)

    try:
        endpoint_path = endpoint_config['endpoint_config_base_location']
        if date_service_needed:
            date_service_uri = endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    # Build Apache config string
    date_service_config = ''
    if date_service_needed:
        date_service_config = DATE_SERVICE_TEMPLATE.replace(
            '{date_service_uri}', date_service_uri).replace('{local_date_service_uri}', LOCAL_DATE_SERVICE_URI)

    proxy_config = None
    proxy_needed = date_service_needed or any(
        layer_config['data_file_uri'] for layer_config in layer_configs)
    if proxy_needed:
        proxy_config = PROXY_MODULE_TEMPLATE

    main_apache_config = MAIN_APACHE_CONFIG_TEMPLATE.replace(
        '{endpoint_path}', endpoint_path)

    layer_config_snippets = '\n'.join([layer_config['apache_config']
                                       for layer_config in layer_configs])

    # Add TWMS if there are any TWMS layers
    twms = any(layer_config.get('twms_config', None)
               for layer_config in layer_configs)
    twms_config = None
    if twms:
        twms_config = bulk_replace(MOD_TWMS_CONFIG_TEMPLATE, [
                                   ('{endpoint_path}', endpoint_path)])

    return generate_string_from_set('\n', ((proxy_config, proxy_needed), (date_service_config, date_service_needed), (main_apache_config, True), (layer_config_snippets, True), (TWMS_MODULE_TEMPLATE, twms), (twms_config, twms)))


def write_apache_config(endpoint_config, apache_config):
    apache_config_path = Path('/etc/httpd/conf.d/oe2-tile-service.conf')
    try:
        apache_config_path = Path(endpoint_config['apache_config_location'])
    except KeyError:
        print(f'"apache_config_location" not found in endpoint config, saving Apache config to {apache_config_path}')
        pass

    # Write out the Apache config
    Path(apache_config_path.parent).mkdir(parents=True, exist_ok=True)
    apache_config_path.write_text(apache_config)
    print(f'Apache config written to {apache_config_path.as_posix()}')


def make_layer_config(endpoint_config, layer_config_path, make_twms=False):
    # Get layer info
    with layer_config_path.open() as f:
        layer_config = yaml.load(f.read())

    # Make sure we have what we need from the layer config
    try:
        layer_id = layer_config['layer_id']
        static = layer_config['static']
        tilematrixset = layer_config['tilematrixset']
        size_x = layer_config['source_mrf']['size_x']
        size_y = layer_config['source_mrf']['size_y']
        tile_size_x = layer_config['source_mrf']['tile_size_x']
        tile_size_y = layer_config['source_mrf']['tile_size_y']
        bands = layer_config['source_mrf']['bands']
        idx_path = Path(layer_config['source_mrf']['idx_path'])
        mimetype = layer_config['mime_type']
    except KeyError as err:
        print(f"{layer_config_filename} is missing required config element {err}")

    # Parse optional stuff in layer config
    year_dir = layer_config['source_mrf'].get('year_dir', False)
    alias = layer_config.get('alias', layer_id)
    empty_tile = layer_config['source_mrf'].get('empty_tile', None)

    data_file_path = layer_config['source_mrf'].get('data_file_path', None)
    data_file_uri = layer_config['source_mrf'].get('data_file_uri', None)
    if not data_file_path and not data_file_uri:
        print(f'No "data_file_path" or "data_file_uri" configured in layer configuration: {layer_config_path}')

    # Make sure we have what we need from the endpoint config
    try:
        endpoint_path = endpoint_config['endpoint_config_base_location']
        if not static:
            date_service_uri = endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    base_idx_path = endpoint_config.get('base_idx_path', None)
    if base_idx_path:
        idx_path = Path(base_idx_path, idx_path)

    base_datafile_path = endpoint_config.get('base_datafile_path', None)
    if base_datafile_path and data_file_path:
        data_file_path = Path(base_datafile_path, data_file_path)

    config_file_path = Path(
        endpoint_path, layer_id, "default", tilematrixset, 'mod_mrf.config')

    # Create Apache snippet

    # Proxy setup for data file (if needed)
    data_file_proxy_snippet = ''
    if data_file_uri:
        data_file_proxy_snippet = DATA_FILE_PROXY_TEMPLATE.replace('{local_data_file_uri}', urlparse(
            data_file_uri).path).replace('{data_file_uri}', data_file_uri)

    # Apache <Directory> stuff
    apache_config = bulk_replace(LAYER_APACHE_CONFIG_TEMPLATE, [
        ('{endpoint_path}', endpoint_path), ('{layer_id}', layer_id), ('{time_enabled}', 'Off' if static else 'On'),  ('{year_dir}', 'On' if year_dir else 'Off'), ('{alias}', alias), ('{tilematrixset}', tilematrixset), ('{config_file_path}', config_file_path.as_posix())])

    # Insert time stuff if applicable (using a regexp to stick it in the
    # <Directory> block)
    if not static:
        date_service_snippet = f'\n        WMTSWrapperTimeLookupUri "{date_service_uri}"'
        apache_config = re.sub(r'(WMTSWrapperEnableTime.*)',
                               r'\1' + date_service_snippet, apache_config)

    # Bundle it all into a data structure
    layer_config_out = {}
    layer_config_out['static'] = static
    layer_config_out['data_file_uri'] = data_file_uri
    layer_config_out['apache_config'] = apache_config

    data_path_str = None
    if data_file_uri:
        data_path_str = f'Redirect {data_file_uri}'
    elif data_file_path:
        data_path_str = f'DataFile {data_file_path}'

    # Add in substitution strings for mod_wmts_wrapper for non-static layers
    if not static:
        if year_dir:
            data_path_str += '/${YYYY}'
            idx_path = idx_path / '${YYYY}'
        data_path_str += '/${filename}'
        idx_path = idx_path / '${filename}'

    main_wmts_config = LAYER_MOD_MRF_CONFIG_TEMPLATE.replace(
        '{size_x}', str(size_x)).replace('{size_y}', str(size_y)).replace('{tile_size_x}', str(tile_size_x)).replace('{tile_size_y}', str(tile_size_y)).replace('{bands}', str(bands)).replace('{idx_path}', idx_path.as_posix())

    # Handle optionals like EmptyTile
    empty_tile_config = None
    if empty_tile:
        empty_tile_config = f'EmptyTile {empty_tile}'

    wmts_config = generate_string_from_set('\n', ((main_wmts_config, True), (
        data_path_str, data_file_uri or data_file_path), (empty_tile_config, empty_tile)))

    # Create mod_mrf configuration file
    layer_config_out['mod_mrf_config'] = {
        'path': config_file_path, 'contents': wmts_config}

    # Build the TWMS config if that's selected
    if make_twms:
        try:
            bbox = layer_config['source_mrf']['bbox']
        except KeyError as err:
            print(f"{layer_config_filename} is missing required config element {err}")

        source_path = Path(endpoint_path, layer_id,
                           'default', '${date}', tilematrixset)
        source_postfix = MIME_TO_EXTENSION[mimetype]
        twms_config = bulk_replace(LAYER_MOD_TWMS_CONFIG_TEMPLATE, [('{size_x}', str(size_x)), ('{size_y}', str(size_y)), (
            '{tile_size_x}', str(tile_size_x)), ('{tile_size_y}', str(tile_size_y)), ('{bands}', str(bands)), ('{source_postfix}', source_postfix), ('{source_path}', source_path.as_posix()), ('{bbox}', bbox)])

        layer_config_out['twms_config'] = {'path': Path(
            endpoint_path, 'twms', layer_id, 'twms.config'), 'contents': twms_config}

    return layer_config_out


def get_layer_configs(endpoint_config, make_twms=False):
    try:
        layer_source = Path(endpoint_config['layer_config_source'])
    except KeyError:
        print("Must specify 'layer_config_source'!")
        sys.exit()

    # Build all source configs - traversing down a single directory level
    if layer_source.is_file():
        layer_configs = [make_layer_config(
            endpoint_config, layer_source, make_twms=make_twms)]
    elif os.layer_source.is_dir(layer_source):
        layer_configs = [make_layer_config(endpoint_config, filepath, make_twms=make_twms) for filepath in layer_source.iterdir(
        ) if filepath.is_file() and filepath.name.endswith('.yaml')]
    return layer_configs


def write_layer_configs(layer_configs):
    # Write out mod_mrf config files
    for layer_config in layer_configs:
        Path.mkdir(layer_config['mod_mrf_config']['path'].parent,
                   parents=True, exist_ok=True)
        layer_config['mod_mrf_config']['path'].write_text(
            layer_config['mod_mrf_config']['contents'])
        print(f'WTMS layer config written to: {layer_config["mod_mrf_config"]["path"]}')

        # Write out TWMS config if included
        if layer_config.get('twms_config', None):
            Path.mkdir(layer_config['twms_config'][
                       'path'].parent, parents=True, exist_ok=True)
            layer_config['twms_config']['path'].write_text(
                layer_config['twms_config']['contents'])
            print(f'TWMS layer config written to: {layer_config["twms_config"]["path"]}')

# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure mod_wmts_wrapper.')
    parser.add_argument('endpoint_config', type=str,
                        help='an endpoint config YAML file')
    parser.add_argument('-t', '--make_twms', action='store_true',
                        help='Generate TWMS configurations')
    args = parser.parse_args()

    endpoint_config = yaml.load(Path(args.endpoint_config).read_text())

    # Build all configs
    layer_configs = get_layer_configs(
        endpoint_config, make_twms=args.make_twms)
    apache_config = make_apache_config(endpoint_config, layer_configs)

    # Write all configs
    write_layer_configs(layer_configs)
    write_apache_config(endpoint_config, apache_config)
    print('All configurations written. Restart Apache for changes to take effect.')
