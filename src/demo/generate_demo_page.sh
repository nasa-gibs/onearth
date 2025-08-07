#!/bin/sh

# Generate dynamic demo page
generate_demo_page() {
    echo "🎨 Generating dynamic demo page..."
    
    OUTPUT_FILE="/var/www/html/demo/index.html"
    CONFIG_DIR="/etc/onearth/config"
    
    # Initialize variables
    WMTS_ENDPOINTS_HTML=""
    WMS_ENDPOINTS_HTML=""
    TWMS_ENDPOINTS_HTML=""
    TOTAL_LAYERS=0
    
    # Define projection order (4326 first, then 3857)
    PROJECTIONS="epsg4326 epsg3857"
    VARIANTS="all best nrt std"
    
    # Process endpoints and collect data for each service type
    for projection in $PROJECTIONS; do
        for variant in $VARIANTS; do
            endpoint_name="${projection}_${variant}"
            endpoint_file="$CONFIG_DIR/endpoint/${endpoint_name}.yaml"
            
            if [ -f "$endpoint_file" ]; then
                layer_dir="$CONFIG_DIR/layers/$projection/$variant"
                layer_count=0
                
                # Count layers - use find to avoid glob expansion issues
                if [ -d "$layer_dir" ]; then
                    layer_count=$(find "$layer_dir" -maxdepth 1 -name "*.yaml" -type f | wc -l)
                    TOTAL_LAYERS=$((TOTAL_LAYERS + layer_count))
                fi
                
                # Show endpoints that have layers OR are reprojected (epsg3857)
                if [ $layer_count -gt 0 ] || [ "$projection" = "epsg3857" ]; then
                    # Determine endpoint type
                    if [ "$projection" = "epsg3857" ]; then
                        endpoint_type="Reprojected from EPSG:4326"
                    else
                        endpoint_type="$layer_count layers"
                    fi
                    
                    # Build service URLs
                    wmts_caps_url="/wmts/$projection/$variant/1.0.0/WMTSCapabilities.xml"
                    wms_caps_url="/wms/$projection/$variant/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
                    twms_caps_url="/twms/$projection/$variant/twms.cgi?request=GetCapabilities"
                    twms_tileservice_url="/twms/$projection/$variant/twms.cgi?request=GetTileService"
                    
                    # Build sample URLs based on projection
                    if [ "$projection" = "epsg3857" ]; then
                        wms_sample_url="/wms/$projection/$variant/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=\${layerId}&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34"
                        twms_sample_url="/twms/$projection/$variant/twms.cgi?request=GetMap&layers=\${layerId}&srs=EPSG:3857&format=image/jpeg&styles=&time=default&width=256&height=256&bbox=-20037508.342789,15028130.342789,-15028130.342789,20037508.342789"
                    else
                        wms_sample_url="/wms/$projection/$variant/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=\${layerId}&CRS=EPSG:4326&STYLES=&WIDTH=512&HEIGHT=512&BBOX=-180,-90,180,90"
                        twms_sample_url="/twms/$projection/$variant/twms.cgi?request=GetMap&layers=\${layerId}&srs=EPSG:4326&format=image/jpeg&styles=default&time=default&width=512&height=512&bbox=-180.000000,-198.000000,108.000000,90.000000"
                    fi
                    
                    # Add to WMTS section
                    WMTS_ENDPOINTS_HTML="$WMTS_ENDPOINTS_HTML
                    <tr>
                        <td><strong>$endpoint_name</strong><br><small>$endpoint_type</small></td>
                        <td><a href=\"$wmts_caps_url\" target=\"_blank\" class=\"btn btn-xs btn-primary\">GetCapabilities</a></td>
                        <td>
                            <button class=\"btn btn-xs btn-default toggle-layers\" type=\"button\" onclick=\"toggleLayers('wmts-layers-$endpoint_name', this)\" style=\"border: 1px dashed #ccc;\">
                                ▼ Show Layers
                            </button>
                            <div id=\"wmts-layers-$endpoint_name\" style=\"display: none; margin-top: 5px;\">
                                <div id=\"wmts-tile-$endpoint_name\" class=\"wmts-tile-info\" data-caps-url=\"$wmts_caps_url\" data-endpoint=\"$endpoint_name\" data-projection=\"$projection\" data-variant=\"$variant\">
                                    <em>Loading layers...</em>
                                </div>
                            </div>
                        </td>
                    </tr>"
                    
                    # Add to WMS section
                    WMS_ENDPOINTS_HTML="$WMS_ENDPOINTS_HTML
                    <tr>
                        <td><strong>$endpoint_name</strong><br><small>$endpoint_type</small></td>
                        <td><a href=\"$wms_caps_url\" target=\"_blank\" class=\"btn btn-xs btn-success\">GetCapabilities</a></td>
                        <td>
                            <button class=\"btn btn-xs btn-default toggle-layers\" type=\"button\" onclick=\"toggleLayers('wms-layers-$endpoint_name', this)\" style=\"border: 1px dashed #ccc;\">
                                ▼ Show Layers
                            </button>
                            <div id=\"wms-layers-$endpoint_name\" style=\"display: none; margin-top: 5px;\">
                                <div id=\"wms-map-$endpoint_name\" class=\"wms-map-info\" data-wms-url=\"$wms_sample_url\" data-endpoint=\"$endpoint_name\">
                                    <em>Loading layers...</em>
                                </div>
                            </div>
                        </td>
                    </tr>"
                    
                    # Add to TWMS section
                    TWMS_ENDPOINTS_HTML="$TWMS_ENDPOINTS_HTML
                    <tr>
                        <td><strong>$endpoint_name</strong><br><small>$endpoint_type</small></td>
                        <td><a href=\"$twms_caps_url\" target=\"_blank\" class=\"btn btn-xs btn-warning\">GetCapabilities</a></td>
                        <td><a href=\"$twms_tileservice_url\" target=\"_blank\" class=\"btn btn-xs btn-warning\">GetTileService</a></td>
                        <td>
                            <button class=\"btn btn-xs btn-default toggle-layers\" type=\"button\" onclick=\"toggleLayers('twms-layers-$endpoint_name', this)\" style=\"border: 1px dashed #ccc;\">
                                ▼ Show Layers
                            </button>
                            <div id=\"twms-layers-$endpoint_name\" style=\"display: none; margin-top: 5px;\">
                                <div id=\"twms-map-$endpoint_name\" class=\"twms-map-info\" data-twms-url=\"$twms_sample_url\" data-endpoint=\"$endpoint_name\">
                                    <em>Loading layers...</em>
                                </div>
                            </div>
                        </td>
                    </tr>"
                fi
            fi
        done
    done
    
    # Generate placeholders
    PROJECTIONS_LIST=$(echo "$PROJECTIONS" | tr ' ' ',')
    GENERATION_TIME=$(date)
    CONFIG_DIR_DISPLAY="${CONFIG_DIR:-Not mounted}"
    MRF_ARCHIVE_DISPLAY="/onearth/archive"
    
    # Get OnEarth version information
    ONEARTH_VERSION_INFO="Unknown"
    if [ -f "/home/oe2/version.sh" ]; then
        # Source the version file from the demo container location
        . /home/oe2/version.sh
        ONEARTH_VERSION_INFO="v${ONEARTH_VERSION}-${ONEARTH_RELEASE}"
    elif [ -f "/version.sh" ]; then
        # Try root location as fallback
        . /version.sh
        ONEARTH_VERSION_INFO="v${ONEARTH_VERSION}-${ONEARTH_RELEASE}"
    fi
    
    # Create the output HTML
    cat > "$OUTPUT_FILE" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css" integrity="sha512-dTfge/zgoMYpP7QbHy4gWMEGsbsdZeCXz7irItjcC3sPUFtf0kuFbDz/ixG7ArTxmDjLXDmezHubeNikyKGVyQ==" crossorigin="anonymous">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap-theme.min.css" integrity="sha384-aUGj/X2zp5rLCbBxumKTCw2Z50WgIr1vs/PFN4praOTvYXWlVyh2UtNUU0KAUhAX" crossorigin="anonymous">
<style>
    /* Prevent table column shifting when layers expand */
    .layer-list {
        max-height: 300px;
        overflow-y: auto;
        word-wrap: break-word;
    }
    .layer-item {
        margin: 2px 0;
    }
    /* Ensure buttons don't wrap */
    .btn-xs {
        white-space: nowrap;
    }
</style>
</head>

<body>
        <div class="container">
                <div class="row">
                <h1>Welcome to OnEarth Local</h1>
                <p>This demo is automatically configured based on your local deployment setup. For more information, visit <a href="https://github.com/nasa-gibs/onearth">https://github.com/nasa-gibs/onearth</a></p>

                <div class="alert alert-info">
                        <strong>🎯 Generated for your setup:</strong> This page was automatically generated based on your MRF data and endpoint configurations.
                </div>

                <hr>

                <h2>🗺️ OpenLayers Demo Endpoints</h2>
                <p>Interactive maps with OpenLayers for testing WMTS endpoints:</p>
                <p><a href="/demo/wmts/epsg4326/" class="btn btn-sm btn-primary">EPSG:4326 Demo</a></p>
                <p><a href="/demo/wmts/epsg3857/" class="btn btn-sm btn-primary">EPSG:3857 Demo</a></p>
                <p><a href="/demo/wmts/epsg3413/" class="btn btn-sm btn-primary">EPSG:3413 Demo</a></p>
                <p><a href="/demo/wmts/epsg3031/" class="btn btn-sm btn-primary">EPSG:3031 Demo</a></p>
                <hr>

                <h2>📡 Service Endpoints</h2>
                <p>These endpoints serve your actual satellite imagery data organized by service type:</p>

                <h3>🗺️ WMTS (Web Map Tile Service)</h3>
                <table class="table table-striped table-condensed" style="table-layout: fixed;">
                    <thead>
                        <tr>
                            <th style="width: 25%;">Endpoint</th>
                            <th style="width: 20%;">GetCapabilities</th>
                            <th style="width: 55%;">Layers</th>
                        </tr>
                    </thead>
                    <tbody>
__WMTS_ENDPOINTS_HTML__
                    </tbody>
                </table>

                <h3>🌍 WMS (Web Map Service)</h3>
                <table class="table table-striped table-condensed" style="table-layout: fixed;">
                    <thead>
                        <tr>
                            <th style="width: 25%;">Endpoint</th>
                            <th style="width: 20%;">GetCapabilities</th>
                            <th style="width: 55%;">Layers</th>
                        </tr>
                    </thead>
                    <tbody>
__WMS_ENDPOINTS_HTML__
                    </tbody>
                </table>

                                <h3>🎯 TWMS (Tiled Web Map Service)</h3>
 
                <table class="table table-striped table-condensed" style="table-layout: fixed;">
                    <thead>
                        <tr>
                            <th style="width: 20%;">Endpoint</th>
                            <th style="width: 15%;">GetCapabilities</th>
                            <th style="width: 15%;">GetTileService</th>
                            <th style="width: 50%;">Layers</th>
                        </tr>
                    </thead>
                    <tbody>
__TWMS_ENDPOINTS_HTML__
                    </tbody>
                </table>

                <hr>

                <h2>🩺 Status Endpoints</h2>
                <p>These endpoints provide health check functionality and testing:</p>

                <table class="table table-striped table-condensed">
                    <thead>
                        <tr>
                            <th>Service</th>
                            <th>Status Check</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>WMTS Status</strong></td>
                            <td><a href="http://localhost/status" target="_blank" class="btn btn-xs btn-primary">Check Status</a></td>
                            <td>Overall WMTS service health check</td>
                        </tr>
                        <tr>
                            <td><strong>WMTS GetCapabilities Status</strong></td>
                            <td><a href="http://localhost/oe-status/wmts.cgi?service=WMTS&request=GetCapabilities&version=1.0.0" target="_blank" class="btn btn-xs btn-primary">GetCapabilities</a></td>
                            <td>Native EPSG:4326 status endpoint capabilities</td>
                        </tr>
                        <tr>
                            <td><strong>Reproject Status</strong></td>
                            <td><a href="/oe-status_reproject/Raster_Status/default/2004-08-01/GoogleMapsCompatible_Level3/0/0/0.jpeg" target="_blank" class="btn btn-xs btn-warning">Sample Tile</a></td>
                            <td>Reprojected EPSG:3857 status tile</td>
                        </tr>
                        <tr>
                            <td><strong>WMS Status</strong></td>
                            <td><a href="/wms/status/" target="_blank" class="btn btn-xs btn-success">Check Status</a></td>
                            <td>WMS service health check</td>
                        </tr>
                    </tbody>
                </table>

                <hr>

                <div class="panel panel-info">
                    <div class="panel-heading">
                        <h4>📋 Setup Information</h4>
                    </div>
                    <div class="panel-body">
                        <p><strong>OnEarth Version:</strong> __ONEARTH_VERSION_INFO__</p>
                        <p><strong>Configuration:</strong> __CONFIG_DIR_DISPLAY__</p>
                        <p><strong>MRF Archive:</strong> __MRF_ARCHIVE_DISPLAY__</p>
                        <p><strong>Available Projections:</strong> __PROJECTIONS_LIST__</p>
                        <p><strong>Total Layers:</strong> __TOTAL_LAYERS__</p>
                        <p><strong>Generated:</strong> __GENERATION_TIME__</p>
                    </div>
                </div>

            </div>
        </div>
        
        <script>
        // Simple toggle function for layer visibility
        function toggleLayers(targetId, button) {
            const target = document.getElementById(targetId);
            if (target.style.display === 'none' || target.style.display === '') {
                target.style.display = 'block';
                button.textContent = '▲ Hide Layers';
            } else {
                target.style.display = 'none';
                button.textContent = '▼ Show Layers';
            }
        }
        
        // Function to parse GetCapabilities and extract all layer information
        function parseCapabilities(xmlText, endpoint, projection, variant) {
                try {
                        const parser = new DOMParser();
                        const xmlDoc = parser.parseFromString(xmlText, "text/xml");
                        
                        // Get all layers
                        const layers = xmlDoc.getElementsByTagName("Layer");
                        if (layers.length === 0) return { noLayers: true };
                        
                        const layerList = [];
                        
                        for (let i = 0; i < layers.length; i++) {
                                const layer = layers[i];
                                
                                // Extract layer identifier
                                const identifierElement = layer.getElementsByTagName("ows:Identifier")[0];
                                if (!identifierElement) continue;
                                const layerId = identifierElement.textContent;
                                
                                // Extract format
                                const formatElements = layer.getElementsByTagName("Format");
                                if (formatElements.length === 0) continue;
                                const format = formatElements[0].textContent.replace('image/', '');
                                
                                // Extract tile matrix set
                                const tmsElements = layer.getElementsByTagName("TileMatrixSetLink");
                                if (tmsElements.length === 0) continue;
                                const tmsElement = tmsElements[0].getElementsByTagName("TileMatrixSet")[0];
                                if (!tmsElement) continue;
                                const tileMatrixSet = tmsElement.textContent;
                                
                                // Build URLs for all service types

                                // Build WMTS URL
                                const wmtsTileUrl = `/wmts/${projection}/${variant}/${layerId}/default/${tileMatrixSet}/0/0/0.${format}`;
                                
                                // Build WMS URL based on projection
                                let wmsUrl;
                                if (projection === 'epsg3857') {
                                        wmsUrl = `/wms/${projection}/${variant}/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=${layerId}&CRS=EPSG:3857&STYLES=&WIDTH=256&HEIGHT=256&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34`;
                                } else if (projection === 'epsg3413') {
                                        wmsUrl = `/wms/${projection}/${variant}/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=${layerId}&CRS=EPSG:3413&STYLES=&WIDTH=512&HEIGHT=512&BBOX=-4194300,-4194300,4194300,4194300`;
                                } else if (projection === 'epsg3031') {
                                        wmsUrl = `/wms/${projection}/${variant}/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=${layerId}&CRS=EPSG:3031&STYLES=&WIDTH=512&HEIGHT=512&BBOX=-4194300,-4194300,4194300,4194300`;
                                } else {
                                        wmsUrl = `/wms/${projection}/${variant}/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/jpeg&TRANSPARENT=true&LAYERS=${layerId}&CRS=EPSG:4326&STYLES=&WIDTH=512&HEIGHT=512&BBOX=-90,-180,90,180`;
                                }
                                
                                // Build TWMS URL based on projection
                                let twmsUrl;
                                if (projection === 'epsg3857') {
                                        twmsUrl = `/twms/${projection}/${variant}/twms.cgi?request=GetMap&layers=${layerId}&srs=EPSG:3857&format=image/jpeg&styles=&time=default&width=256&height=256&bbox=-20037508.342789,-20037508.342789,20037508.342789,20037508.342789`;
                                } else if (projection === 'epsg3413') {
                                        twmsUrl = `/twms/${projection}/${variant}/twms.cgi?request=GetMap&layers=${layerId}&srs=EPSG:3413&format=image/jpeg&styles=&time=default&width=512&height=512&bbox=1048576,-524288,1572864,0`;
                                } else if (projection === 'epsg3031') {
                                        twmsUrl = `/twms/${projection}/${variant}/twms.cgi?request=GetMap&layers=${layerId}&srs=EPSG:3031&format=image/jpeg&styles=&time=default&width=512&height=512&bbox=1048576,-524288,1572864,0`;
                                } else {
                                        twmsUrl = `/twms/${projection}/${variant}/twms.cgi?request=GetMap&layers=${layerId}&srs=EPSG:4326&format=image/jpeg&styles=default&time=default&width=512&height=512&bbox=-180.000000,-198.000000,108.000000,90.000000`;
                                }
                                
                                layerList.push({
                                        layerId: layerId,
                                        format: format,
                                        tileMatrixSet: tileMatrixSet,
                                        wmtsTileUrl: wmtsTileUrl,
                                        wmsUrl: wmsUrl,
                                        twmsUrl: twmsUrl
                                });
                        }
                        
                        return {
                                layers: layerList
                        };
                } catch (error) {
                        console.error('Error parsing capabilities:', error);
                        return null;
                }
        }

        // Load layer information for all endpoints
        document.addEventListener('DOMContentLoaded', function() {
                const wmtsTileElements = document.querySelectorAll('.wmts-tile-info');
                
                wmtsTileElements.forEach(element => {
                        const capsUrl = element.getAttribute('data-caps-url');
                        const endpoint = element.getAttribute('data-endpoint');
                        const projection = element.getAttribute('data-projection');
                        const variant = element.getAttribute('data-variant');
                        
                        fetch(capsUrl)
                                .then(response => response.text())
                                .then(xmlText => {
                                        const layerInfo = parseCapabilities(xmlText, endpoint, projection, variant);
                                        if (layerInfo && layerInfo.noLayers) {
                                                element.innerHTML = '<em>No layers found</em>';
                                                
                                                // Also update WMS and TWMS elements with no layers message
                                                const wmsElement = document.getElementById(`wms-map-${endpoint}`);
                                                if (wmsElement) {
                                                        wmsElement.innerHTML = '<em>No layers found</em>';
                                                }
                                                
                                                const twmsElement = document.getElementById(`twms-map-${endpoint}`);
                                                if (twmsElement) {
                                                        twmsElement.innerHTML = '<em>No layers found</em>';
                                                }
                                        } else if (layerInfo && layerInfo.layers) {
                                                // Create WMTS layer list
                                                let wmtsHtml = '<div class="layer-list">';
                                                layerInfo.layers.forEach(layer => {
                                                        wmtsHtml += `<div class="layer-item" style="margin: 2px 0;">`;
                                                        wmtsHtml += `<a href="${layer.wmtsTileUrl}" target="_blank" class="btn btn-xs btn-info">${layer.layerId}</a> `;
                                                        wmtsHtml += `<small>${layer.format} | ${layer.tileMatrixSet}</small>`;
                                                        wmtsHtml += `</div>`;
                                                });
                                                wmtsHtml += '</div>';
                                                element.innerHTML = wmtsHtml;
                                                
                                                // Create WMS layer list
                                                const wmsElement = document.getElementById(`wms-map-${endpoint}`);
                                                if (wmsElement) {
                                                        let wmsHtml = '<div class="layer-list">';
                                                        layerInfo.layers.forEach(layer => {
                                                                wmsHtml += `<div class="layer-item" style="margin: 2px 0;">`;
                                                                wmsHtml += `<a href="${layer.wmsUrl}" target="_blank" class="btn btn-xs btn-info">${layer.layerId}</a> `;
                                                                wmsHtml += `<small>GetMap</small>`;
                                                                wmsHtml += `</div>`;
                                                        });
                                                        wmsHtml += '</div>';
                                                        wmsElement.innerHTML = wmsHtml;
                                                }
                                                
                                                // Create TWMS layer list
                                                const twmsElement = document.getElementById(`twms-map-${endpoint}`);
                                                if (twmsElement) {
                                                        let twmsHtml = '<div class="layer-list">';
                                                        layerInfo.layers.forEach(layer => {
                                                                twmsHtml += `<div class="layer-item" style="margin: 2px 0;">`;
                                                                twmsHtml += `<a href="${layer.twmsUrl}" target="_blank" class="btn btn-xs btn-info">${layer.layerId}</a> `;
                                                                twmsHtml += `<small>GetMap</small>`;
                                                                twmsHtml += `</div>`;
                                                        });
                                                        twmsHtml += '</div>';
                                                        twmsElement.innerHTML = twmsHtml;
                                                }
                                        } else {
                                                element.innerHTML = '<em>Could not parse layer info</em>';
                                                
                                                // Also update WMS and TWMS elements with error message
                                                const wmsElement = document.getElementById(`wms-map-${endpoint}`);
                                                if (wmsElement) {
                                                        wmsElement.innerHTML = '<em>Could not parse layer info</em>';
                                                }
                                                
                                                const twmsElement = document.getElementById(`twms-map-${endpoint}`);
                                                if (twmsElement) {
                                                        twmsElement.innerHTML = '<em>Could not parse layer info</em>';
                                                }
                                        }
                                })
                                .catch(error => {
                                        console.error('Error fetching capabilities:', error);
                                        element.innerHTML = '<em>Error loading capabilities</em>';
                                        
                                        // Also update WMS and TWMS elements with error message
                                        const wmsElement = document.getElementById(`wms-map-${endpoint}`);
                                        if (wmsElement) {
                                                wmsElement.innerHTML = '<em>Error loading capabilities</em>';
                                        }
                                        
                                        const twmsElement = document.getElementById(`twms-map-${endpoint}`);
                                        if (twmsElement) {
                                                twmsElement.innerHTML = '<em>Error loading capabilities</em>';
                                        }
                                });
                });
        });
        </script>

    </body>

    </html>
EOF
    
    # Substitute variables in the generated HTML using a temporary file approach
    # This is safer than sed when dealing with complex HTML content
    export CONFIG_DIR_DISPLAY MRF_ARCHIVE_DISPLAY PROJECTIONS_LIST TOTAL_LAYERS GENERATION_TIME ONEARTH_VERSION_INFO
    
    # Create a temporary file for the HTML content replacement
    temp_file=$(mktemp)
    
    # Replace simple variables with sed (safe ones)
    sed "s|__CONFIG_DIR_DISPLAY__|$CONFIG_DIR_DISPLAY|g" "$OUTPUT_FILE" > "$temp_file"
    sed -i "s|__MRF_ARCHIVE_DISPLAY__|$MRF_ARCHIVE_DISPLAY|g" "$temp_file"
    sed -i "s|__PROJECTIONS_LIST__|$PROJECTIONS_LIST|g" "$temp_file"
    sed -i "s|__TOTAL_LAYERS__|$TOTAL_LAYERS|g" "$temp_file"
    sed -i "s|__GENERATION_TIME__|$GENERATION_TIME|g" "$temp_file"
    sed -i "s|__ONEARTH_VERSION_INFO__|$ONEARTH_VERSION_INFO|g" "$temp_file"
    
    # Replace the complex HTML content using a different approach
    # Write the service endpoints to separate temp files
    wmts_temp=$(mktemp)
    wms_temp=$(mktemp)
    twms_temp=$(mktemp)
    echo "$WMTS_ENDPOINTS_HTML" > "$wmts_temp"
    echo "$WMS_ENDPOINTS_HTML" > "$wms_temp"
    echo "$TWMS_ENDPOINTS_HTML" > "$twms_temp"
    
    # Use awk to replace the placeholders with file content
    awk -v wmts_file="$wmts_temp" -v wms_file="$wms_temp" -v twms_file="$twms_temp" '
        /__WMTS_ENDPOINTS_HTML__/ {
            while ((getline line < wmts_file) > 0) {
                print line
            }
            close(wmts_file)
            next
        }
        /__WMS_ENDPOINTS_HTML__/ {
            while ((getline line < wms_file) > 0) {
                print line
            }
            close(wms_file)
            next
        }
        /__TWMS_ENDPOINTS_HTML__/ {
            while ((getline line < twms_file) > 0) {
                print line
            }
            close(twms_file)
            next
        }
        { print }
    ' "$temp_file" > "$OUTPUT_FILE"
    
    # Clean up temp files
    rm -f "$temp_file" "$wmts_temp" "$wms_temp" "$twms_temp"
    
    echo "   ✅ Demo page generated successfully!"
    echo "   📍 Found $(echo "$WMTS_ENDPOINTS_HTML" | grep -c "<tr>") configured endpoint(s)"
    echo "   🌍 Found $(echo "$PROJECTIONS" | wc -w) projection(s): $PROJECTIONS_LIST"
    echo "   📊 Total layers: $TOTAL_LAYERS"
}

# Execute the function
generate_demo_page