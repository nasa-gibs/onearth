#!/bin/bash
ct() {
  while read a
  do
    echo $a
  done
}

QS=${QUERY_STRING%%GetMap*}
if [[ -z ${QS##*=} ]]
then
  if [[ $QUERY_STRING == *jpeg* ]]
  then
    echo -e "Content-type: image/jpeg\n"
    cat black.jpg
  else
    echo -e "Content-type: image/png\n"
    cat transparent.png
  fi
  exit
else
  if [[ $QUERY_STRING == *GetCapabilities* ]]
  then
    echo -e "Content-type: text/xml\n"
    cat .lib/getCapabilities.xml
#    IFS= ct <.lib/getCapabilities.xml
    exit
  else
    if [[ $QUERY_STRING == *GetTileService* ]]
    then
      echo -e "Content-type: text/xml\n"
      cat .lib/getTileService.xml
      exit
    fi
  fi
  echo -e "Content-type: text/html\n"
  echo "<body>This is not a full WMS server!</body>"
fi
