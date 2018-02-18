from collections import namedtuple

from mutagen.flac import FLAC


"""Tag names supported for albums and tracks."""
FLACKUP_TAGS = ['TITLE', 'ARTIST', 'PERFORMER', 'GENRE', 'DATE', 'HIDE']


"""A subset of FLAC cue sheet track data.

See also: https://xiph.org/flac/format.html#cuesheet_track
"""
CueSheetTrack = namedtuple('CueSheetTrack', 'number offset type')


class CueSheet(object):
    """A subset of FLAC cue sheet data.

    Variables:
    - tracks: List of CueSheetTrack instances, including lead-out.

    See also: https://xiph.org/flac/format.html#metadata_block_cuesheet
    """

    def __init__(self, mutagen_cuesheet):
        def track(t):
            return CueSheetTrack(t.track_number, t.start_offset, t.type)

        self._mcs = mutagen_cuesheet
        self.tracks = [track(t) for t in mutagen_cuesheet.tracks]

    @property
    def is_cd(self):
        """Return True if this is an audio CD cue sheet."""
        return self._mcs.compact_disc

    @property
    def lead_in(self):
        """Return the number of lead-in samples."""
        return self._mcs.lead_in_samples

    @property
    def audio_track_numbers(self):
        """Return a list of audio track numbers, excluding lead-out."""
        def is_audio(track):
            return track.type == 0 and track.number != 170

        return [t.number for t in self.tracks if is_audio(t)]


class Tags(object):
    """Flackup album and track tags.

    Supported tag names for albums and tracks:
    - TITLE
    - ARTIST
    - PERFORMER
    - GENRE
    - DATE
    - HIDE ('yes' to ignore for conversion/playback)

    This class supports only one string value per tag.

    See also: https://www.xiph.org/vorbis/doc/v-comment.html
    """

    def __init__(self, mutagen_tags):
        if mutagen_tags is not None:
            self._tags = mutagen_tags
        else:
            self._tags = {}

    def album_tags(self):
        """Return a dictionary of album-level tags."""
        return self._collect_tags('', *FLACKUP_TAGS)

    def track_tags(self, number):
        """Return a dictionary of track-level tags."""
        prefix = 'TRACK_%02d_' % number
        return self._collect_tags(prefix, *FLACKUP_TAGS)

    def update_album(self, tags):
        """Update album-level tags.

        Returns True if anything changed.
        """
        return self._update_tags(tags, '', *FLACKUP_TAGS)

    def update_track(self, number, tags):
        """Update track-level tags.

        Returns True if anything changed.
        """
        prefix = 'TRACK_%02d_' % number
        return self._update_tags(tags, prefix, *FLACKUP_TAGS)

    def _collect_tags(self, prefix, *args):
        result = {}
        for name in args:
            key = prefix + name
            if key in self._tags:
                result[name] = self._tags[key][0]
        return result

    def _update_tags(self, tags, prefix, *args):
        changed = False
        for name in args:
            key = prefix + name
            if name not in tags and key not in self._tags:
                continue
            elif name in tags and key not in self._tags:
                self._tags[key] = tags[name]
                changed = True
            elif name not in tags and key in self._tags:
                del self._tags[key]
                changed = True
            elif tags[name] != self._tags[key][0]:
                del self._tags[key]
                self._tags[key] = tags[name]
                changed = True
        return changed


class FileInfo(object):
    """Read and write FLAC metadata.

    Variables:
    - filename: The FLAC file.
    - parse_ok: True if the file was parsed successfully.
                If False, cuesheet and tags will be None.
    - parse_exception: The exception raised during parsing, or None.
    - cuesheet: The file's CueSheet, or None.
    - tags: The file's Tags, or None.
    """

    def __init__(self, filename):
        self.filename = str(filename)
        self.parse_ok = False
        self.parse_exception = None
        self.cuesheet = None
        self.tags = None
        self.parse()

    def parse(self):
        """Read the FLAC file and update the variables."""
        try:
            self._flac = FLAC(self.filename)
            if self._flac.cuesheet is not None:
                self.cuesheet = CueSheet(self._flac.cuesheet)
                self.tags = Tags(self._flac.tags)
            else:
                self.cuesheet = None
                self.tags = None
            self.parse_ok = True
            self.parse_exception = None
        except Exception as e:
            self.parse_ok = False
            self.parse_exception = e
            self.cuesheet = None
            self.tags = None

    def update(self):
        """Save the current variables and re-parse the FLAC file."""
        self._flac.save()
        self.parse()
