#!/usr/bin/env python3
"""
Copyright (c) 2002-2025, California Institute of Technology.
All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright notice,
     this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
  3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
     the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
     endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import argparse
import json
import logging
import numpy as np
import numpy.typing as npt
from osgeo import gdal, osr
from pathlib import Path
from PIL import Image
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from typing import Tuple, List, Dict, Union, Optional

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert GeoJSON UV direction vectors to PNG or TIFF images for WebGL shaders"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        metavar="FILE",
        help="Path to input GeoJSON file containing UV direction vectors",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="FILE",
        help="Path to save output tile. Default is same location/filename as input with png/tif extension",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        help="Override the auto-detected grid resolution (in degrees)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["png", "tiff", "tif"],
        default="png",
        help="Output format: 'png' for 8-bit quantized or 'tiff'/'tif' for 32-bit float (default: png)",
    )
    return parser.parse_args()


def load_geojson(file_path: Path) -> List[Tuple[float, float, float, float]]:
    """
    Load and parse GeoJSON file into a list of (lon, lat, u, v) tuples.

    Arguments:
        file_path (Path) -- Path to the GeoJSON file

    Returns:
        list[tuple[float...]] -- List of tuples containing (longitude, latitude, u_value, v_value)
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    points = []
    for feature in data["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        u_val = feature["properties"]["u"]
        v_val = feature["properties"]["v"]
        points.append((lon, lat, u_val, v_val))

    return points


def detect_resolution(
    points: List[Tuple[float, float, float, float]]
) -> Tuple[float, float]:
    """
    Detect the grid resolution from the input points.

    Arguments:
        points (list[tuple[float..]]) -- List of (lon, lat, u, v) tuples

    Returns:
        tuple[float, float] -- (longitude_resolution, latitude_resolution)
    """
    # Extract all unique longitudes and latitudes
    lons = sorted(set(p[0] for p in points))
    lats = sorted(set(p[1] for p in points))

    # Calculate differences between consecutive values
    lon_diffs = np.diff(lons)
    lat_diffs = np.diff(lats)

    # Use minimum non-zero difference as the resolution
    # Filter out any differences that are effectively zero due to floating point precision
    eps = 1e-10
    lon_diffs = lon_diffs[lon_diffs > eps]
    lat_diffs = lat_diffs[lat_diffs > eps]

    lon_res = float(np.round(np.min(lon_diffs), decimals=4))
    lat_res = float(np.round(np.min(lat_diffs), decimals=4))

    logger.info(f"Detected resolution: {lon_res}° longitude, {lat_res}° latitude")

    return lon_res, lat_res


def create_grid(
    points: List[Tuple[float, float, float, float]], resolution: Optional[float] = None
) -> Tuple[
    npt.NDArray[np.float32],
    npt.NDArray[np.float32],
    Dict[str, np.float32],
    Dict[str, Union[int, float]],
]:
    """
    Create a regular grid from input points with interpolation for custom resolutions.

    Arguments:
        points (list[tuple[float...]]) -- List of (lon, lat, u, v) tuples
        resolution (float | None) -- Optional override for grid resolution in degrees

    Returns:
        Tuple containing:
        - grid_u (npt.NDArray[np.float32]) -- numpy array of u values
        - grid_v (npt.NDArray[np.float32]) -- numpy array of v values
        - value_ranges (Dict) -- Dictionary with min/max values for u and v
        - grid_info (Dict) -- Dictionary with grid dimensions and resolution
    """
    # Get input data values
    input_lons = np.array([p[0] for p in points])
    input_lats = np.array([p[1] for p in points])
    input_u = np.array([p[2] for p in points], dtype=np.float32)
    input_v = np.array([p[3] for p in points], dtype=np.float32)
    u_min: np.float32 = input_u.min()
    u_max: np.float32 = input_u.max()
    v_min: np.float32 = input_v.min()
    v_max: np.float32 = input_v.max()
    
    # Auto-detect input resolution or use provided resolution
    input_lon_res, input_lat_res = detect_resolution(points)

    # When using IDW, set the threshold for setting an ouput grid point to
    # nodata as 1.1x the input grid resolution
    max_distance = 1.1 * max(input_lon_res, input_lat_res)
    
    if resolution is None:
        lon_res, lat_res = input_lon_res, input_lat_res
    else:
        lon_res = lat_res = resolution
        logger.info(f"Using provided resolution: {resolution}°")
    
    # Create output grid
    grid_lons = np.arange(-180, 180, lon_res)
    grid_lats = np.arange(90, -90, -lat_res)
    width = len(grid_lons)
    height = len(grid_lats)
    
    # Initialize grids with NaN to identify unmapped points
    grid_u = np.full((height, width), np.nan, dtype=np.float32)
    grid_v = np.full((height, width), np.nan, dtype=np.float32)
    
    # Check if resolutions are very close (exact match case)
    use_exact_match = (abs(lon_res - input_lon_res) < 1e-6 and 
                      abs(lat_res - input_lat_res) < 1e-6)
    
    if use_exact_match:
        # If resolutions match, use direct mapping which is faster for simple cases
        # logger.info("Using exact matching for grid points (resolutions match)")
        # Create lookup dictionaries for grid indices
        lon_index = {round(lon, 6): i for i, lon in enumerate(grid_lons)}
        lat_index = {round(lat, 6): i for i, lat in enumerate(grid_lats)}
        
        # Fill grid points
        points_mapped = 0
        for lon, lat, u_val, v_val in points:
            lon_key = round(lon, 6)
            lat_key = round(lat, 6)
            if lon_key in lon_index and lat_key in lat_index:
                x = lon_index[lon_key]
                y = lat_index[lat_key]
                grid_u[y, x] = u_val
                grid_v[y, x] = v_val
                points_mapped += 1
        
        logger.info(f"Mapped {points_mapped} out of {len(points)} points to grid")
    else:
        # If resolutions differ, use Inverse Distance Weighted interpolation
        logger.info(f"Input resolution ({input_lon_res:.6f}°, {input_lat_res:.6f}°) differs from output resolution ({lon_res:.6f}°, {lat_res:.6f}°)")
        logger.info("Using Inverse Distance Weighted interpolation")
        
        # Create 2D coordinate arrays for the output grid
        lon_grid, lat_grid = np.meshgrid(grid_lons, grid_lats)
        
        # Combine input coordinates
        input_coords = np.column_stack((input_lons, input_lats))
        
        # Create KD-Tree for faster nearest neighbor lookup
        logger.info("Building KD-Tree for interpolation")
        tree = cKDTree(input_coords)
        
        # Flatten the output grid coordinates for vectorized processing
        output_coords = np.column_stack((lon_grid.flatten(), lat_grid.flatten()))
        
        # Find 4 nearest points using KD-Tree (much faster than brute force)
        logger.info(f"Finding nearest neighbors for {len(output_coords)} output points")
        distances, indices = tree.query(output_coords, k=4)

        # Create a mask for points that are within the max_distance
        valid_mask = np.any(distances <= max_distance, axis=1)
        logger.info(f"Found {np.sum(valid_mask)}/{len(valid_mask)} grid points within threshold")
        
        # Only process points within max_distance
        valid_output_coords = output_coords[valid_mask]
        valid_indices = np.arange(len(output_coords))[valid_mask]
        
        if len(valid_output_coords) > 0:
            # Find 4 nearest points for IDW interpolation (only for valid points)
            distances, indices = tree.query(valid_output_coords, k=4)
            
            # Handle edge case where distances might be zero
            # Add small epsilon to avoid division by zero
            distances = np.maximum(distances, 1e-10)
            
            # Calculate IDW weights
            weights = 1.0 / distances
            weights_sum = np.sum(weights, axis=1, keepdims=True)
            normalized_weights = weights / weights_sum
            
            # Apply weights to the values
            u_values = np.sum(input_u[indices] * normalized_weights, axis=1)
            v_values = np.sum(input_v[indices] * normalized_weights, axis=1)
            
            # Map interpolated values back to their original positions in the flattened grid
            flat_grid_u = np.full(height * width, np.nan)
            flat_grid_v = np.full(height * width, np.nan)
            
            flat_grid_u[valid_indices] = u_values
            flat_grid_v[valid_indices] = v_values
            
            # Reshape back to grid
            grid_u = flat_grid_u.reshape(height, width).astype(np.float32)
            grid_v = flat_grid_v.reshape(height, width).astype(np.float32)
        else:
            logger.warning("No valid points found within max_distance threshold")
        
        logger.info("Interpolation complete")
    
    value_ranges = {"u_min": u_min, "u_max": u_max, "v_min": v_min, "v_max": v_max}
    
    grid_info = {
        "width": width,
        "height": height,
        "lon_res": lon_res,
        "lat_res": lat_res,
    }
    
    return grid_u, grid_v, value_ranges, grid_info


def create_world_file(
    output_path: Path, 
    grid_info: Dict[str, Union[float, int]]
) -> None:
    """
    Create a world file for geospatial referencing of the image.
    
    Arguments:
        output_path (Path) -- Path to the output image file
        grid_info (Dict[str, Union[float, int]]) -- Dictionary with grid dimensions and resolution
    """
    # Determine world file extension
    base_ext = output_path.suffix.lower()
    world_ext = {
        '.png': '.pgw',
        '.tif': '.tfw',
        '.tiff': '.tfw',
    }.get(base_ext, '.wld')
    
    world_file_path = output_path.with_suffix(world_ext)
    
    # Calculate world file parameters
    pixel_width = 360.0 / grid_info["width"]      # X size of a pixel
    pixel_height = -180.0 / grid_info["height"]   # Y size of a pixel (negative)
    x_rotation = 0.0
    y_rotation = 0.0
    top_left_x = -180.0 + (pixel_width / 2)       # X coordinate of center of top-left pixel
    top_left_y = 90.0 + (pixel_height / 2)        # Y coordinate of center of top-left pixel
    
    # Write world file
    with open(world_file_path, 'w') as f:
        f.write(f"{pixel_width:.10f}\n")
        f.write(f"{x_rotation:.10f}\n")
        f.write(f"{y_rotation:.10f}\n")
        f.write(f"{pixel_height:.10f}\n")
        f.write(f"{top_left_x:.10f}\n")
        f.write(f"{top_left_y:.10f}\n")
    
    logger.info(f"Created world file: {world_file_path}")


def save_png(
    grid_u: npt.NDArray[np.float32],
    grid_v: npt.NDArray[np.float32],
    value_ranges: Dict[str, np.float32],
    grid_info: Dict[str, Union[float, int]],
    output_path: Path,
) -> None:
    """
    Create 8-bit PNG image from UV grids.

    Arguments:
        grid_u (npt.NDArray[np.float32]) -- numpy array of u values
        grid_v (npt.NDArray[np.float32]) -- numpy array of v values
        value_ranges (Dict[str, np.float32]) -- Dictionary with min/max values for u and v
        grid_info  (Dict[str, Union[float, int]]) -- Dictionary with grid dimensions
    """
    width, height = grid_info["width"], grid_info["height"]
    img = Image.new("RGBA", (width, height))
    img_data = img.load()

    u_range = value_ranges["u_max"] - value_ranges["u_min"]
    v_range = value_ranges["v_max"] - value_ranges["v_min"]

    # Fill unmapped points with zeros
    grid_u = np.nan_to_num(grid_u, nan=value_ranges["u_min"])
    grid_v = np.nan_to_num(grid_v, nan=value_ranges["v_min"])

    for y in range(height):
        for x in range(width):
            u_val = grid_u[y, x]
            v_val = grid_v[y, x]

            # Scale to 0-255
            r = int(255 * (u_val - value_ranges["u_min"]) / u_range)
            g = int(255 * (v_val - value_ranges["v_min"]) / v_range)
            b = 0
            a = 255

            img_data[x, y] = (r, g, b, a)

    img.save(output_path, optimize=True, compress_level=9)

    # The world file is required for MRF generation.
    create_world_file(output_path, grid_info)

    return img


def save_geotiff(
    grid_u: npt.NDArray[np.float32],
    grid_v: npt.NDArray[np.float32],
    grid_info: Dict[str, Union[float, int]],
    output_path: Path,
) -> None:
    """
    Save the 2-band float arrays grid_u and grid_v to a GeoTIFF file with
    georeferencing for a global lat/lon extent (EPSG:4326).

    Arguments:
        grid_u (npt.NDArray[np.float32]) -- numpy array of u values
        grid_v (npt.NDArray[np.float32]) -- numpy array of v values
        grid_info  (Dict[str, Union[float, int]]) -- Dictionary with grid dimensions
        output_path (Path) -- Path to save output file
    """
    width, height = grid_info["width"], grid_info["height"]

    gdal.UseExceptions()
    driver = gdal.GetDriverByName("GTiff")
    # Create(output, x_size, y_size, bands, datatype)
    dataset = driver.Create(str(output_path), width, height, 2, gdal.GDT_Float32)
    if not dataset:
        raise RuntimeError(
            f"GDAL initialization failed: could not create {output_path}"
        )

    """
    Define the GeoTransform
    GeoTransform is [
        top-left x, pixel width, rotation,
        top-left y, rotation, pixel height
    ]
    For a global coverage GTiff:
      - top-left x (west) = -180
      - pixel width = 360 / width
      - top-left y (north) = 90
      - pixel height = -180 / height
    """
    pixel_width = 360.0 / width
    pixel_height = -180.0 / height
    geotransform = [-180.0, pixel_width, 0.0, 90.0, 0.0, pixel_height]
    dataset.SetGeoTransform(geotransform)

    # Set the spatial reference / projection (EPSG:4326 => WGS84 lat/lon)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)  # WGS84
    dataset.SetProjection(srs.ExportToWkt())

    # Write the arrays
    band1 = dataset.GetRasterBand(1)  # U component
    band2 = dataset.GetRasterBand(2)  # V component

    band1.SetColorInterpretation(gdal.GCI_RedBand)  # Or another appropriate type
    band2.SetColorInterpretation(gdal.GCI_GreenBand)

    band1.SetDescription("U component")
    band2.SetDescription("V component")

    dataset.SetMetadataItem("BANDS_SEMANTIC", "VECTOR_COMPONENT")
    dataset.SetMetadataItem("BAND_1_SEMANTIC", "VECTOR_COMPONENT_U")
    dataset.SetMetadataItem("BAND_2_SEMANTIC", "VECTOR_COMPONENT_V")

    band1.SetMetadataItem("UNITS", "m/s")
    band2.SetMetadataItem("UNITS", "m/s")

    # Use -9999.0 as a nodata value for floats. May need refinement.
    grid_u = np.nan_to_num(grid_u, nan=-9999.0)
    grid_v = np.nan_to_num(grid_v, nan=-9999.0)
    band1.SetNoDataValue(-9999.0)
    band2.SetNoDataValue(-9999.0)

    band1.WriteArray(grid_u)
    band2.WriteArray(grid_v)

    # Flush and close the dataset
    band1.FlushCache()
    band2.FlushCache()
    dataset.FlushCache()
    dataset = None  # closes the file

    logger.info(f"Saved GeoTIFF to: {output_path}")


def main() -> None:
    """Main function to run the conversion process."""
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s (%(asctime)s): %(message)s"
    )

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        # due to "choices" keyword in argparse, we know we need to add a leading "."
        format = "." + args.format
        output_path = args.input_file.with_suffix(format)

    try:
        points = load_geojson(args.input_file)
        grid_u, grid_v, value_ranges, grid_info = create_grid(points, args.resolution)

        if args.format == "png":
            save_png(grid_u, grid_v, value_ranges, grid_info, output_path)
        else:  # tiff
            # value_ranges dict is not required since we are not quanitizing
            save_geotiff(grid_u, grid_v, grid_info, output_path)

        # Log summary
        logger.info("Processing complete!")
        logger.info(f"Grid dimensions: {grid_info['width']}x{grid_info['height']}")
        logger.info(
            f"U range: {value_ranges['u_min']:.4f} to {value_ranges['u_max']:.4f}"
        )
        logger.info(
            f"V range: {value_ranges['v_min']:.4f} to {value_ranges['v_max']:.4f}"
        )

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise


if __name__ == "__main__":
    main()
