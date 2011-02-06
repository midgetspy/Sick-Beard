from lib.hachoir_metadata.version import VERSION as __version__
from lib.hachoir_metadata.metadata import extractMetadata

# Just import the module,
# each module use registerExtractor() method
import lib.hachoir_metadata.archive
import lib.hachoir_metadata.audio
import lib.hachoir_metadata.file_system
import lib.hachoir_metadata.image
import lib.hachoir_metadata.jpeg
import lib.hachoir_metadata.misc
import lib.hachoir_metadata.program
import lib.hachoir_metadata.riff
import lib.hachoir_metadata.video

