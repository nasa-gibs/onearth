## onearth_logs.py

OnEarth custom log generator for creating metrics

```
Usage: onearth_logs.py --input [file] --output [file] --config [logs.xml] --tilematrixsetmap [tilematrixsetmap.xml] --date [YYYY-MM-DD] --quiet --tail --wmts_translate_off

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c CONFIG, --config=CONFIG
                        Full path of log configuration file.  Default:
                        logs.xml
  -d LOGDATE, --date=LOGDATE
                        Filter log for specified date [YYYY-MM-DD]
  -i INPUT, --input=INPUT
                        The full path of the input log file
  -m TILEMATRIXSETMAP, --tilematrixsetmap=TILEMATRIXSETMAP
                        Full path of configuration file containing
                        TileMatrixSet mappings.  Default: tilematrixsetmap.xml
  -o OUTPUT, --output=OUTPUT
                        The full path of the output log file
  -q, --quiet           Suppress log output to terminal
  -t, --tail            Tail the log file
  -w, --wmts_translate_off
                        Do not translate Tiled-WMS tile requests to WMTS
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
