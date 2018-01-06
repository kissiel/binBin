#!/usr/bin/env python3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import json
import os
import subprocess
import sys

from shutil import which


description = """
Probe a video file to see if it's encoded in a way that the default
Playstation 4's Media Player can handle. If not, transcode/transmux with
ffmpeg. If C4PS4_TARGET envvar is defined, the output will be written to the
directory pointed by that envvar.
""".strip()

ALLOWED_ACODECS = ['aac']
ALLOWED_VCODECS = ['x264']

def main():
    for tool in ['ffmpeg', 'ffprobe']:
        if not which(tool):
            raise SystemExit(
                "{} not found in the system!".format(tool))

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('input_file')
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        raise SystemExit(
            "{} doesn't look like a valid input file!".format(args.input_file))

    target_dir = os.environ.get('C4PS4_TARGET', os.curdir)
    if not os.path.isdir(target_dir):
        raise SystemExit(
            "{} doesn't look like a good target directory!".format(target_dir))

    probe(args.input_file)


def probe(media_file):
    """Identify container, video, and audio codec of a file."""
    cmd = ['ffprobe', '-print_format', 'json', '-v', 'quiet', '-show_format',
           '-show_streams', media_file] 
    output = subprocess.check_output(cmd).decode(sys.stdout.encoding)
    info = json.loads(output)
    container = info['format']['format_name']
    audio_candidates = []
    for stream in info['streams']:
        if stream['codec_type'] == 'video':
            print('Found video stream: #{}, codec: {}'.format(
                stream['index'], stream['codec_name']))
            if stream['codec_name'] in ALLOWED_VCODECS:
                video_codec = stream['codec_name']
                continue
        if stream['codec_type'] == 'audio':
            print('Found audio stream: #{}, codec: {}'.format(
                stream['index'], stream['codec_name']))
            audio_candidates.append(stream)
    def is_in_english(stream):
        return stream['tags'].get('language', '') in ['eng', 'english']
    english_streams = [ac for ac in audio_candidates if is_in_english(ac)]
    if english_streams:
        audio_candidates = english_streams
    for stream in audio_candidates:
        if stream['codec_name'] in ALLOWED_ACODECS:
            # good codec - no transcoding needed
            pass


    return audio_candidates

    

if __name__ == '__main__':
    main()


