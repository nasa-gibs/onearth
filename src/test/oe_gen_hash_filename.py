#!/usr/bin/env python3
import hashlib
import datetime

import sys
import optparse

def get_hash_prefix(filename):
    md5hash = hashlib.md5()
    md5hash.update(filename)
    hash_value = str(md5hash.hexdigest())
    return hash_value[:4]

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('-l', '--layer', action='store', type='string', dest='layer', default='BlueMarble', help='layer name to incorporate into file name')
    parser.add_option('-t', '--time_epoch', action='store', type='int', dest='epoch', default=sys.maxsize, help='time epoch to convert and incorporate into file name')
    parser.add_option('-e', '--extension', action='store', type='string', dest='extension', default='', help='filename that will be converted to hash filename')
    (options, args) = parser.parse_args()

    if options.layer == '' or options.epoch == sys.maxsize:
        sys.exit(-1)

    #print options.layer, options.epoch, options.extension
    date_str = ''
    try:
        date_str = datetime.datetime.utcfromtimestamp(int(options.epoch)).strftime('%Y%j%H%M%S')
    except ValueError:
        sys.exit(-2)
    newname = options.layer + '-' + date_str
    hprefix = get_hash_prefix(newname)
#     hashname = hprefix + '-' + newname + options.extension
    hashname = newname + options.extension
    print(hashname)
