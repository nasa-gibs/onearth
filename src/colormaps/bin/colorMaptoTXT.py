#!/usr/bin/python3
import argparse
from typing import List, Optional, Tuple
from xml.dom import minidom

# This is not -sys.float_info.min, but it works for this application.
FLOAT_LOW_BOUND = "-100000000000000000000000000000000000000000000000000000000000000000000000000000"
FLOAT_HIGH_BOUND = "100000000000000000000000000000000000000000000000000000000000000000000000000000"

class XmlParseError(Exception):
    pass


def convertEntryValue(
        entryValue: str,
        scale: Optional[float],
        offset: Optional[float]) -> str:
    '''
    Using a given scaleFactor and offset, convert the entryValue from its original value in the
    colormap XML to the value that will be used in the text colormap.

    :param entryValue: A string containing a value that can be converted to a float.
    :param scale: An optional float specifying the scale factor to multiply by the cmap values.
    :param offset: An optional float specifying an amount to add to the cmap values.
    :param offset: The assumed output unit, or one explicitly specified via an input argument.

    :returns: A string containing the scaled and offset colormap quantization level.
    '''
    optionalScale: float = scale or 1.0
    optionalOffset: float = offset or 0.0
    return str(optionalScale * float(entryValue) + optionalOffset)


def parseColorMapEntryElement(
        cmapEntryElement: minidom.Element,
        scale: Optional[float],
        offset: Optional[float]) -> str:
    '''
    Parse a <ColorMapEntry> tag.

    :param colorMapElement: A minidom.Element called "ColorMapEntry" that contains the required
    attributes "rgb" and "transparent" at a minimum.
    :param scale: An optional float specifying the scale factor to multiply by the cmap values.
    :param offset: An optional float specifying an amount to add to the cmap values.

    :returns: A single line str containing the parsed colormap entry in GDAL txt format.
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

        # Handle INF: If the lower bound is -INF, use a value of -9999. This does not seem
        # robust, but is based off of the example outputs in layer-configs.
        if lineValue.upper() == "-INF":
            #lineValue = "-9999"
            lineValue = FLOAT_LOW_BOUND
        elif lineValue.upper() == "INF":
            # Technically this branch should never be reached, since the lower bound is always used.
            lineValue = FLOAT_HIGH_BOUND
        else:
            # Handle units, idempotent if both scale and offset are None.
            # Note that INF has to be handled first because this function casts to float.
            lineValue = convertEntryValue(lineValue, scale, offset)

            # Always represent floating point values with two decimal places, unless -INF
            lineValue = f"{float(lineValue):.2f}"
        
    lineRgb: str = entryRgb.replace(",", " ")

    # Add an alpha channel value of 0 if this entry is transparent
    lineTransparent: str = " 0" if entryTransparent else ""

    return f"{lineValue} {lineRgb}{lineTransparent}\n"


def parseColorMapElement(
        colorMapElement: minidom.Element,
        scale: Optional[float],
        offset: Optional[float],
        round: bool = False) -> str:
    '''
    Parse a <ColorMap> tag.

    :param colorMapElement: A minidom.Element called "ColorMap" that contains <ColorMapEntry>
    tags as children (may not be direct children).
    :param scale: An optional float specifying the scale factor to multiply by the cmap values.
    :param offset: An optional float specifying an amount to add to the cmap values.
    :param round: Output the colormap in the round to floor mode if True.
    
    :returns: A str containing the parsed colormap entries in GDAL txt format.

    :raises XmlParseError: If no ColorMapEntry tags are present in the input colormap XML.
    '''
    cmapEntryNodes: List[minidom.Element] = colorMapElement.getElementsByTagName("ColorMapEntry")
    if len(cmapEntryNodes) == 0:
        raise XmlParseError(f"No elements called \"ColorMapEntry\" were found in the document.")

    #minValue, maxValue = findMinMaxValues(cmapEntryNodes)

    cmapStr: str = ""
    cmapLinePrev: str = ""
    for entryNode in cmapEntryNodes:
        cmapLine: str = parseColorMapEntryElement(
            entryNode,
            scale,
            offset
        )

        # If using the "round to the floor" mode, use a small offset + the previous line's value as the "floor"
        # the next colormap quantization value. The R, G, B at this level has to come from the most recently
        # parsed line.
        if round and cmapLinePrev != "":
            cmapLinePrevVal: str = cmapLinePrev.split()[0]
            cmapLineRgb: str = " ".join(cmapLine.split()[1:])
            # Do not add a "floor" line for colormap lines that are no data or -INF
            if cmapLinePrevVal != "nv" and cmapLinePrevVal != FLOAT_LOW_BOUND:
                cmapLineFloor = f"{(float(cmapLinePrevVal) + 0.001):.3f} {cmapLineRgb}\n"
                cmapStr += cmapLineFloor
        cmapStr += cmapLine
        cmapLinePrev = cmapLine

    return cmapStr


def parseColorMapDoc(
        colormapFile: str,
        scale: Optional[float],
        offset: Optional[float],
        round: bool = False) -> str:
    '''
    Parses input colormap XML document (a string referencing a filepath) using the xml.dom.minidom
    module and converts it to a text format. The text format has the following specification:
    [sourceValue] [red] [green] [blue] [<optional> alpha]

    NOTE: How should multiple ColorMaps in the same file actually be handled? The No Data
    ColorMap and a single other ColorMap are fine for this format, but the spec allows for
    multiple ColorMaps to exist in the same document. Currently the code appends them together.

    :param colormap_file: A string filepath to the colormap XML document input.
    :param scale: An optional float specifying the scale factor to multiply by the cmap values.
    :param offset: An optional float specifying an amount to add to the cmap values.
    :param round: Output the colormap in the round to floor mode if True.

    :returns: A string containing the parsed colormap information.

    :raises ValueError: If either the user-provided scale or offset are unable to be cast to float.
    :raises XmlParseError:  If no ColorMap tags are present in the input colormap XML.
    '''
    # Input sanitization, rely on error handling in minidom.parse for the colormapFile argument.
    try:
        parsedScale: Optional[float] = float(scale) if scale is not None else None
        parsedOffset: Optional[float] = float(offset) if offset is not None else None
    except ValueError as e:
        print(f"Provided input parameters are invalid, scale: {scale}, offset: {offset}")
        raise e

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
        #unitsAttr: Optional[minidom.Attr] = cmapNode.attributes.get("units")
        colorMapLines: str = parseColorMapElement(
            cmapNode,
            parsedScale,
            parsedOffset,
            round
        )

        # Use this janky heuristic to decide if the parsed colormap was the nodata one.
        # The title attribute of the ColorMap tag also gives this information.
        if colorMapLines.startswith("nv"):
            # Prepend the nodata line to the beginning of the document string
            docStr = colorMapLines + docStr
        else:
            docStr += colorMapLines

    # Remove trailing newline from final entry
    #return docStr.strip()
    # Just kidding, don't strip trailing newline
    return docStr


def colorMapToTxt(
        args: argparse.Namespace) -> None:
    '''
    Top-level function for converting a colormap file into a text file compatible with GDAL.

    :param args: An argparse namespace containing the arguments from the CLI.

    :returns: None, the colormap information is printed to stdout or saved to a plain-text file as a side effect.
    '''
    colorMapText: str = parseColorMapDoc(args.c, args.scale, args.offset, args.round)
    if args.o is None:
        print(colorMapText)
    else:
        args.o.write(colorMapText)
        print(f"Successfully wrote colormap data to {args.o.name}")
    return


def cli() -> None:
    '''
    Command line interface for this script. Invokes colorMapToTxt function as a side effect.

    :returns: None, invokes colorMapToTxt as a side effect.
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
        "--scale",
        type=float,
        help="Optionally specify the scale factor for the output colormap." + \
             " This can sometimes be found in the CMR variable metadata. For example," + \
             " a colormap with percent units might need --scale 0.01 to appear correct."
    )
    parser.add_argument(
        "--offset",
        type=float,
        help="Optionally specify the offset for the output colormap." + \
             " This can sometimes be found in the CMR variable metadata. For example," + \
             " a colormap in units of degC might need --scale 273.15 to convert to Kelvin."
    )
    parser.add_argument(
        "-o",
        metavar="outfile",
        type=argparse.FileType("w"), # Ascii encoding
        help="Output filename to use for the text file colormap. If unused, the colormap will" + \
             " be printed to stdout."
    )
    parser.add_argument(
        "--round",
        action="store_true",
        help="Create the colormap with a \"round to the floor\" mode, where the same color value " + \
             "is used across an entire quantization level, with no interpolation."
    )
    args: argparse.Namespace = parser.parse_args()
    colorMapToTxt(args)
    return


if __name__ == "__main__":
    cli()