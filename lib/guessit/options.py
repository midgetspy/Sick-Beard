from optparse import OptionParser

option_parser = OptionParser(usage='usage: %prog [options] file1 [file2...]')
option_parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False,
                  help='display debug output')
option_parser.add_option('-p', '--properties', dest='properties', action='store_true', default=False,
              help='Display properties that can be guessed.')
option_parser.add_option('-l', '--values', dest='values', action='store_true', default=False,
          help='Display property values that can be guessed.')
option_parser.add_option('-s', '--transformers', dest='transformers', action='store_true', default=False,
              help='Display transformers that can be used.')
option_parser.add_option('-i', '--info', dest='info', default='filename',
                  help='the desired information type: filename, hash_mpc or a hash from python\'s '
                       'hashlib module, such as hash_md5, hash_sha1, ...; or a list of any of '
                       'them, comma-separated')
option_parser.add_option('-n', '--name-only', dest='name_only', action='store_true', default=False,
              help='Parse files as name only. Disable folder parsing, extension parsing, and file content analysis.')
option_parser.add_option('-t', '--type', dest='type', default=None,
                  help='the suggested file type: movie, episode. If undefined, type will be guessed.')
option_parser.add_option('-a', '--advanced', dest='advanced', action='store_true', default=False,
                  help='display advanced information for filename guesses, as json output')
option_parser.add_option('-y', '--yaml', dest='yaml', action='store_true', default=False,
              help='display information for filename guesses as yaml output (like unit-test)')
option_parser.add_option('-d', '--demo', action='store_true', dest='demo', default=False,
                  help='run a few builtin tests instead of analyzing a file')
