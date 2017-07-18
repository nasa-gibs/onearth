/**
 * GIBS Web Examples
 *
 * Copyright 2013 - 2014 United States Government as represented by the
 * Administrator of the National Aeronautics and Space Administration.
 * All Rights Reserved.
 *
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

window.onload = function() {
    proj4.defs("EPSG:3031",
        "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 " +
        "+datum=WGS84 +units=m +no_defs");
    ol.proj.get("EPSG:3031").setExtent([-4194304, -4194304, 4194304, 4194304]);

    var map = new ol.Map({
          view: new ol.View({
    center: [0,0],
    zoom: 2,
    projection: ol.proj.get("EPSG:3031"),
  }),
	target: "map",
        renderer: ["canvas", "dom"]
    });

    var blue_marble = new ol.layer.Image({
	extent: [-4194304, -4194304, 4194304, 4194304],
	source: new ol.source.ImageWMS({
	  url: 'wms.cgi',
	  params: {'LAYERS': 'blue_marble', 'FORMAT': 'image/jpeg'}
	})
    })
    
map.addLayer(blue_marble);
};
