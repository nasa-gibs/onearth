# OnEarth Storage

## Meta Raster Format (MRF) files

OnEarth relies on [MRF](https://github.com/nasa-gibs/mrf/blob/master/README.md) files for serving raster imagery and vector tiles.

MRF files generally consist of three files: header (mrf), index (idx), and data (ppg/pjg/ptf/pvt/lerc) files.

## Default Storage Locations

MRF Files: `/onearth/`
MRF IDX Files: `/onearth/idx/`

## Recommended Storage Options

If using AWS, we recommend mounting an EFS volume for the MRF index files in `/onearth/idx/` and storing the data files on S3.
EFS is recommended for the index files for two reasons: 1) it provides the access speed needed for quick lookups in an index;
2) due to the sparse nature of the index files, storage options that don't support sparse files, such as S3, will make the files
appear much larger than they really are.