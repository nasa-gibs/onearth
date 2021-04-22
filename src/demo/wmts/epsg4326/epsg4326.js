/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
let globalDateString;

function makeTileLoadFunction() {
    return (imageTile, src) => {
        imageTile.getImage().src =
            src + "&TIME=" + (globalDateString || "default");
    };
}

window.onload = function() {
    //CONFIGURATION
    //Set the EPSG projection here. EPSG:4326, 3857, 3413, and 3031 are supported.
    var EPSGProjection = "EPSG:4326";

    //Set the maximum number of zoom levels. This will depend on the average number of TileMatrixSets for each layer at this endpoint.
    var maxZoomLevels = 12;

    //If using vector tiles, specify their identifiers
    var vectorLayers = [];

    //Set locations for endpoint and getCapabilities
    var endpointUrl = "/wmts/epsg4326/best/wmts.cgi?";
    var getCapabilitiesLocation = "/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml";
    //END CONFIGURATION

    //proj4.js needed for arctic/antarctic projections.
    if(EPSGProjection === "EPSG:3413" || EPSGProjection === "EPSG:3031") {
        proj4.defs(EPSGProjection,
        "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 " +
        "+datum=WGS84 +units=m +no_defs");
        ol.proj.get(EPSGProjection).setExtent([-4194304, -4194304, 4194304, 4194304]);
    }
    
    var mapProjection = ol.proj.get(EPSGProjection);
    var maxRes;
    var extents;

    var testVectorLayerStyle = new ol.style.Style({
        fill: new ol.style.Fill({
          color: 'blue'
        }),
        stroke: new ol.style.Stroke({
          color: 'blue',
          width: 1
        }),
        image: new ol.style.Circle({
            radius: 1,
            fill: new ol.style.Fill({
                color: 'blue'
            }),
            stroke: new ol.style.Stroke({
                color: 'blue',
                width: 1
            })
        })
    });
    
    //Extents and resolution info from: https://wiki.earthdata.nasa.gov/display/GIBS/GIBS+API+for+Developers
    switch (EPSGProjection) {
        case "EPSG:4326":
            maxRes = 0.5625;
            extents = [-180, -90, 180, 90];
            break;
        case "EPSG:3857":
            maxRes = 156543.03390625;
            extents = [-20037508.34, -20037508.34, 20037508.34, 20037508.34];
            break;
        case ("EPSG:3413" || "EPSG:3031"):
            maxRes = 8192.0;
            extents = [-4194304, -4194304, 4194304, 4194304];
            break;
    }

    var map = new ol.Map({
        view: new ol.View({
            maxResolution: maxRes,
            projection: mapProjection,
            extent: extents,
            center: [0, 0],
            zoom: 1,
            maxZoom: maxZoomLevels
        }),
        target: "map",
        renderer: ["canvas", "dom"]
    });
    
    var req = new XMLHttpRequest();
    //Callback to handle getCapabilities and build layers
    req.onreadystatechange = function() {
    	if (req.readyState == 4 && req.status == 200) {
            //Use OpenLayers to parse getCapabilities
    		var parser = new ol.format.WMTSCapabilities();
    		var response = req.response.toString().replace(/<Identifier>/g,"<ows:Identifier>").replace(/<\/Identifier>/g,"<\/ows:Identifier>");
    		var result = parser.read(response);
    		var layers = result.Contents.Layer;
    		var tileMatrixSets = result.Contents.TileMatrixSet;
            var mapMetersPerUnit = mapProjection.getMetersPerUnit();    
    		
            for(var i=0; i<layers.length; i++) {
    			var layerName = layers[i].Identifier;
    			var tileMatrix;
    			var tileMatrixIds = [];
    			var resolutions = [];
                /*
                Ideally, this would use ol.source.WMTS.optionsFromCapabilities to generate the layer source from getCapabilites,
                but as of now, it only supports TileMatrixSets with names that correspond exactly to the 2 projections it natively supports.
                So we have to parse the options and calculate the resolutions manually.
                */
    			for(var j=0; j<tileMatrixSets.length; j++) {
    				if(tileMatrixSets[j].Identifier == layers[i].TileMatrixSetLink[0].TileMatrixSet) {
    					tileMatrixSet = tileMatrixSets[j];
    					for(var k=0; k<tileMatrixSet.TileMatrix.length; k++) {
    						tileMatrixIds.push(tileMatrixSet.TileMatrix[k].Identifier);
    						resolutions.push(tileMatrixSet.TileMatrix[k].ScaleDenominator * 0.28E-3 / mapMetersPerUnit);
    					}
    				}
    			}

                if(vectorLayers.includes(layerName)) {
                    var tms = layers[i].TileMatrixSetLink[0].TileMatrixSet;
                    var source = new ol.source.VectorTile({
                        format: new ol.format.MVT(),
                        tileGrid: ol.tilegrid.createXYZ({maxZoom: parseInt(tms.match(/^GoogleMapsCompatible_Level(\d)/)[1]) - 1}),
                        tilePixelRatio: 16,
                        url: `/wmts/epsg3857/all/wmts.cgi?layer=${layerName}&tilematrixset=${tms}&Service=WMTS&Request=GetTile&Version=1.0.0&Format=application%2Fx-protobuf&TileMatrix={z}&TileCol={x}&TileRow={y}`
                    });
                    var newLayer = new ol.layer.VectorTile({
                        source,
                        style: testVectorLayerStyle,
                    });
                } else {
        			var source = new ol.source.WMTS({
    		            url: endpointUrl,
          			    layer: layerName,
    			        format: layers[i].Format[0],
    			        matrixSet: layers[i].TileMatrixSetLink[0].TileMatrixSet,
    			        tileGrid: new ol.tilegrid.WMTS({
    			            origin: [tileMatrixSet.TileMatrix[0].TopLeftCorner[0], tileMatrixSet.TileMatrix[0].TopLeftCorner[1]],
    			            matrixIds: tileMatrixIds,
    			            tileSize: tileMatrixSet.TileMatrix[0].TileHeight,
    				    resolutions: resolutions
    			        })
        		   	 });
        			var newLayer = new ol.layer.Tile({
        				source,
        			});
                }
                newLayer.set('id', layerName);
                newLayer.setVisible(false);
    			map.addLayer(newLayer);
    			var dropDown = document.getElementById("layer-select");
                //Add string for new checkbox to dropdown div
    			var newCheckboxTagString = '<label class="layer-checkbox-label"><input type="checkbox" value="' + layerName + '" class="layer-checkbox"> ' + layerName + '</label>';
    			dropDown.innerHTML += newCheckboxTagString;
    		}
        }
    }
    req.open("GET", getCapabilitiesLocation, true);
    req.send();

    //Event handler for checkbox items (collapsing menu itself is in Bootstrap)
    var dropDown = document.getElementById("layer-select");
    dropDown.addEventListener("change", function(evt) {
    	var pickedLayerName = evt.target.value;
    	var layerCollection = map.getLayers();

        //For a layer that is selected, remove it and then put it at the highest index. If deselected, just make it invisible.
    	for(var i=0; i<layerCollection.getLength(); i++) {
    		var layer = layerCollection.item(i);
    		var layerName = layer.get('id');
    		if(layerName !== pickedLayerName) continue;
			if(evt.target.checked) {
				map.getLayers().removeAt(i);
				map.getLayers().insertAt(layerCollection.getLength(), layer);
				layer.setVisible(true);
			} else {
				layer.setVisible(false);
			}
    	}
    });
    
    const date_picker = flatpickr("#datePicker", {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        altInput: true,
        altFormat: "F j, Y H:i:S",
        defaultDate: new Date(),
        time_24hr: true,
        onChange: (selectedDates, dateStr, instance) => {
            const date = selectedDates[0];
            const month = (date.getMonth() + 1).toString().padStart(2, "0");
            const day = date
                .getDate()
                .toString()
                .padStart(2, "0");
            const hours = date
                .getHours()
                .toString()
                .padStart(2, "0");
            const minutes = date
                .getMinutes()
                .toString()
                .padStart(2, "0");
            const seconds = date
                .getSeconds()
                .toString()
                .padStart(2, "0");
            globalDateString = `${date.getFullYear()}-${month}-${day}T${
                hours
            }:${minutes}:${seconds}Z`;
            map.getLayers().forEach(layer => {
                layer.getSource().setTileLoadFunction(makeTileLoadFunction());
            });
        }
    });
};
