## mrfgen.py

This tool is used to help automate the generation of MRF files. It takes in a list of image files or a single global image and generates an MRF output that is configured for use with the OnEarth server.

## Installation

Yum install
```Shell
sudo yum -y install onearth-mrfgen-*.el6.x86_64.rpm
```

Manual install
```Shell
cp src/mrfgen <installation location>
```

## Usage

```
Usage: mrfgen.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIGURATION_FILENAME, --configuration_filename=CONFIGURATION_FILENAME
                        Full path of configuration filename.  Default:
                        ./mrfgen_configuration_file.xml
  -d, --data_only       Only output the MRF data, index, and header files
  -s SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
```

## Samples

* [Sample mrfgen configuration file](mrfgen_configuration_sample.xml)
* [mrfgen configuration schema](mrfgen_configuration.xsd)

## Tutorial