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
let globalDateString;

function makeTileLoadFunction() {
    return (imageTile, src) => {
        imageTile.getImage().src =
            src + "&TIME=" + (globalDateString || "default");
    };
}

window.onload = function() {
    var map = new ol.Map({
        view: new ol.View({
            maxResolution: 8192.0,
            projection: ol.proj.get("EPSG:3413"),
            extent: [-4194304, -4194304, 4194304, 4194304],
            center: [0, 0],
            zoom: 1,
            maxZoom: 5,
        }),
        target: "map",
        renderer: ["canvas", "dom"]
    });

    var source = new ol.source.WMTS({
        url: "/wmts/epsg3013/all/wmts.cgi",
        layer: "MODIS_Terra_CorrectedReflectance_TrueColor",
        extent: [-4194304, -4194304, 4194304, 4194304],
        format: "image/jpeg",
        matrixSet: "EPSG3013_250m",
        tileGrid: new ol.tilegrid.WMTS({
            origin: [-4194304, 4194304],
            resolutions: [
                8192.0,
                4096.0,
                2048.0,
                1024.0,
                512.0,
                256.0
            ],
            matrixIds: [0, 1, 2, 3, 4, 5],
            tileSize: 512
        })
    });

    var layer = new ol.layer.Tile({
        source: source
    });

    map.addLayer(layer);

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
