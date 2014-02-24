#!/bin/bash
#

srcdir=$1


for i in $srcdir/*mrf
do
  outname=`basename $i .mrf`.xml

  FIRST_PATTERN=TRUE
  while IFS= read a

  do

# Pick the format
    [[ ( $a == *Compression* ) && ( $a == *PNG* ) ]] && FORMAT="image/png"
    [[ ( $a == *Compression* ) && ( $a == *JPEG* ) ]] && FORMAT="image/jpeg"

    # Note that the TileMatrixSet has Levels+1 TileMatrix's (yes, I know that's not the correct spelling) 
    [[ ( $a == *Levels* ) && ( $a == *1* ) ]] && TILEMATRIXSET="EPSG4326_64km"
    [[ ( $a == *Levels* ) && ( $a == *2* ) ]] && TILEMATRIXSET="EPSG4326_32km"
    [[ ( $a == *Levels* ) && ( $a == *3* ) ]] && TILEMATRIXSET="EPSG4326_16km"
    [[ ( $a == *Levels* ) && ( $a == *4* ) ]] && TILEMATRIXSET="EPSG4326_8km"
    [[ ( $a == *Levels* ) && ( $a == *5* ) ]] && TILEMATRIXSET="EPSG4326_4km"
    [[ ( $a == *Levels* ) && ( $a == *6* ) ]] && TILEMATRIXSET="EPSG4326_2km"
    [[ ( $a == *Levels* ) && ( $a == *7* ) ]] && TILEMATRIXSET="EPSG4326_1km"
    [[ ( $a == *Levels* ) && ( $a == *8* ) ]] && TILEMATRIXSET="EPSG4326_500m"
    [[ ( $a == *Levels* ) && ( $a == *9* ) ]] && TILEMATRIXSET="EPSG4326_250m"

# Note the assumption that Compression and Levels procede Pattern!

    if [[ $a == *Pattern* ]]
    then
      if [[ $FIRST_PATTERN == TRUE ]]
      then
# Pick the layer name
	LAYER=${a##*LAYER=}
	LAYER=${LAYER%%&*}
# Get start and end dates
        startdate=""
        enddate=""
        startdate=`grep -oP '(?<=<StartDate>).*?(?=</StartDate>)' $srcdir/$i`
        enddate=`grep -oP '(?<=<EndDate>).*?(?=</EndDate>)' $srcdir/$i`
# Get metadata
		METADATA=""
		METADATA=`grep -oP '(?<=<Metadata>).*?(?=</Metadata>)' $srcdir/$i`
# Build the pattern
        if [ $LAYER != population -a $LAYER != sedac_bound ]; then

          echo "      <Layer>"
          echo "         <ows:Title>$LAYER</ows:Title>"
          # Need Abstract here
          echo "         <ows:WGS84BoundingBox>"
          echo "            <ows:LowerCorner>-180 -90</ows:LowerCorner>"
          echo "            <ows:UpperCorner>180 90</ows:UpperCorner>"
          echo "         </ows:WGS84BoundingBox>"
          echo "         <ows:Identifier>$LAYER</ows:Identifier>"
          if [ "$METADATA" != "" ]; then
        	 echo "         <ows:Metadata xlink:href=\"$METADATA\" xlink:title=\"Styled Layer Descriptor (SLD): Data - RGB Mapping\"/>"
       	  fi
          echo "         <Style isDefault=\"true\">"
          echo "            <ows:Title>default</ows:Title>"
          echo "            <ows:Identifier>default</ows:Identifier>"
                            # Need LegendURL
          echo "         </Style>"
          echo "         <Format>$FORMAT</Format>"
	      if [ "$startdate" != "" ]; then
	          echo "         <Dimension>" 
	          echo "           <ows:Identifier>time</ows:Identifier>"
	          echo "           <UOM>ISO8601</UOM>"
	          echo "           <Default>$enddate</Default>"
	          echo "           <Current>false</Current>"
	          echo "           <Value>$startdate/$enddate/P1D</Value>"
	          echo "         </Dimension>" 
	      fi
          # Need InfoFormat
          echo "         <TileMatrixSetLink>"
          echo "            <TileMatrixSet>$TILEMATRIXSET</TileMatrixSet>"
          echo "         </TileMatrixSetLink>"
          echo "      </Layer>"
        fi
        FIRST_PATTERN=FALSE
      fi
    fi
  done <$i > $outname
done
