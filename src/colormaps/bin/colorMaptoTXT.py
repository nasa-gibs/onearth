#!/usr/bin/python3
import argparse
import dataclasses
import re
from typing import List, Optional
from xml.dom import minidom


class XmlParseError(Exception):
    pass


def converEntryValue(
        entryValue: str,
        sourceUnits: str,
        outUnits: str) -> str:
    '''
    Using the units specified for this ColorMap, convert to the expected unit for the output colormap.
    Currently only handles % -> decimal and °C <-> K.

    :param entryValue: A string containing a value that can be converted to a float.
    :param sourceUnits: A string containing the unit parsed from the ColorMap tag.
    :param outUnits: The assumed output unit, or one explicitly specified via an input argument.
    '''
    convertedValue: str = entryValue
    
    if sourceUnits == "%":
        # If the unit is %, convert the integer entryValue to a decimal.
        convertedValue = f"{float(entryValue) / 100.0:.2f}"
    elif sourceUnits == "°C" and outUnits == "K":
        convertedValue = f"{float(entryValue) + 273.15:.2f}"
    elif sourceUnits == "K" and (outUnits == "°C" or outUnits == "C" or outUnits == "degC"):
        convertedValue = f"{float(entryValue) - 273.15:.2f}"
    
    return convertedValue

def parseColorMapEntryElement(
        cmapEntryElement: minidom.Element,
        sourceUnits: Optional[str],
        outUnits: Optional[str]) -> str:
    '''
    Parse a <ColorMapEntry> tag.
    TO DO: What are we supposed to with label attributes for Classification type colormaps?

    :param colorMapElement: A minidom.Element called "ColorMapEntry" that contains the required
    attributes "rgb" and "transparent" at a minimum.
    :param sourceUnits: The unit of the sourceValue/value attributes of the ColorMapEntry tag.
    :outUnits: The unit of the output colormap, if specified.
    :return: A single line str containing the parsed colormap entry in GDAL txt format.
    '''
    # Throw KeyError if any of these required attributes are not found in the <ColorMapEntry>
    entryRgb: str = cmapEntryElement.attributes["rgb"].value
    entryTransparent: bool = cmapEntryElement.attributes["transparent"].value.lower() == "true"

    # "No Data" <ColorMapEntry> tags will have an optional nodata attribute
    noDataAttr: Optional[minidom.Attr] = cmapEntryElement.attributes.get("nodata")
    entryNoData: bool = False
    if noDataAttr is not None:
        entryNoData = noDataAttr.value.lower() == "true"

    # The sourceValue attribute is unused per the other colormap conversion scripts,
    # so only value is parsed. The value attribute is optional.
    valueAttr: Optional[minidom.Attr] = cmapEntryElement.attributes.get("value")
    entryValue: str = ""
    if valueAttr is not None:
        entryValue = valueAttr.value
        
    # Convert the parsed attribute information into a line of the colormap file formatted
    # as a string, following the GDAL convention.
    # [lower bound of value or nv] [space separated rgb] [0 if transparent == True, else not present]
    if entryNoData == True:
        # GDAL uses the special string nv in colormaps to denote nodata or no value
        lineValue: str = "nv"
    else:
        # Take the lower bound of the range from the value string. Value is formatted like this:
        # [0.00,0.15) or [1] or [0,+INF]
        # Where either number in the range can be a float, int, or +/-INF.
        lineValue: str = entryValue.strip("[]()").split(",")[0]

        # Handle units
        if sourceUnits is not None:
            lineValue = converEntryValue(lineValue, sourceUnits, outUnits)

        # Handle INF: If the lower bound is -INF, use a value of -9999. This does not seem
        # robust, but is based off of the example outputs in layer-configs.
        if lineValue.upper() == "-INF":
            # Note possible bug: if the other entries are floating point, this value may need .00 appended
            lineValue = "-9999"
        elif lineValue.upper() == "INF":
            # Technically this branch should never be reached, since the lower bound is always used.
            lineValue = "9999"
        
    lineRgb: str = entryRgb.replace(",", " ")

    # Add an alpha channel value of 0 if this entry is transparent
    lineTransparent: str = " 0" if entryTransparent else ""

    return f"{lineValue} {lineRgb}{lineTransparent}\n"


def parseColorMapElement(
        colorMapElement: minidom.Element,
        sourceUnits: Optional[str] = None,
        outUnits: Optional[str] = None) -> str:
    '''
    Parse a <ColorMap> tag.

    :param colorMapElement: A minidom.Element called "ColorMap" that contains <ColorMapEntry>
    tags as children (may not be direct children).
    :param sourceUnits: The unit of the sourceValue/value attributes of the ColorMapEntry tags.
    :param outUnits: The unit of the output colormap, if specified.
    :return: A str containing the parsed colormap entries in GDAL txt format.
    '''
    # TO DO: Consider reading the title attribute from the element and using that to decide outUnits.

    cmapEntryNodes: List[minidom.Element] = colorMapElement.getElementsByTagName("ColorMapEntry")
    if len(cmapEntryNodes) == 0:
        raise XmlParseError(f"No elements called \"ColorMapEntry\" were found in the document.")

    cmapStr: str = ""
    for entryNode in cmapEntryNodes:
        cmapStr += parseColorMapEntryElement(entryNode, sourceUnits, outUnits)

    return cmapStr


def parseColorMapDoc(
        colormapFile: str,
        outUnits: Optional[str]) -> str:
    '''
    Parses input colormap XML document (a string referencing a filepath) using the xml.dom.minidom
    module and converts it to a text format. The text format has the following specification:
    [sourceValue] [red] [green] [blue] [<optional> alpha]

    TO DO: How should multiple ColorMaps in the same file actually be handled? The No Data
    ColorMap and a single other ColorMap are fine for this format, but the spec allows for
    multiple ColorMaps to exist in the same document. Currently the code appends them together.

    :param colormap_file: A string filepath to the colormap XML document input.
    :param outUnits: An optional string specifying the units to use in the output colormap.
    :return: A string containing the parsed colormap information.
    '''
    doc: minidom.Document = minidom.parse(colormapFile)
    
    # Retrieve all <ColorMap> tags from the document, if none are found report a helpful error
    colorMapNodes: List[minidom.Element] = doc.documentElement.getElementsByTagName("ColorMap")
    if len(colorMapNodes) == 0:
        raise XmlParseError(f"No elements called \"ColorMap\" were found in the document.")

    # The string for the overall document. While the ordering of colormaps should be preserved
    # from the original document in general, the nodata colormap (or colormap entry) should be
    # at the top of the string.
    docStr: str = ""
    for cmapNode in colorMapNodes:
        # Units may or may not be present for any given ColorMap tag.
        unitsAttr: Optional[minidom.Attr] = cmapNode.attributes.get("units")
        if unitsAttr is None:
            colorMapLines: str = parseColorMapElement(cmapNode)
        else:
            colorMapLines: str = parseColorMapElement(
                cmapNode,
                sourceUnits=unitsAttr.value,
                outUnits=outUnits
            )

        # Use this janky heuristic to decide if the parsed colormap was the nodata one.
        # The title attribute of the ColorMap tag also gives this information.
        if colorMapLines.startswith("nv"):
            # Prepend the nodata line to the beginning of the document string
            docStr = colorMapLines + docStr
        else:
            docStr += colorMapLines

    # Remove trailing newline from final entry
    return docStr.strip()


def colorMapToTxt(
        args: argparse.Namespace) -> None:
    '''
    Top-level function for converting a colormap file into a text file compatible with GDAL.

    :param args: An argparse namespace containing the arguments from the CLI.
    :return: None, a .txt file representing the colormap information is created as a side effect.
    '''
    colorMapText: str = parseColorMapDoc(args.c, args.u)
    if args.o is None:
        print(colorMapText)
    else:
        with open(args.o, "w") as outfp:
            outfp.write(colorMapText)
        print(f"Successfully wrote colormap data to {args.o}")
    return


def cli() -> None:
    '''
    Command line interface for this script. Invokes colorMapToTxt function as a side effect.

    :return: None, invokes colorMapToTxt as a side effect.
    '''
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    # Normally it would be simpler to use a required positional argument, but this 
    # specification matches the usage of the other scripts.
    parser.add_argument(
        "-c",
        metavar="colormap",
        required=True,
        help="Path to colormap file to be converted."
    )
    parser.add_argument(
        "-u",
        metavar="unit",
        help="Optionally specify the unit to use in the output colormap." + \
             " C, K, °C, or degC are supported values. This is helpful" + \
             " if you want to ensure that e.g., a Temperature Anomaly" + \
             "colormap is in Celsius or a Temperature colormap is in K."
    )
    parser.add_argument(
        "-o",
        metavar="outfile",
        help="Output filename to use for the text file colormap. If unused, the colormap will" + \
             " be printed to stdout."
    )
    args: argparse.Namespace = parser.parse_args()
    colorMapToTxt(args)
    return


if __name__ == "__main__":
    cli()