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
ALLOWED_VCODECS = ['h264']


def main():
    for tool in ['ffmpeg', 'ffprobe']:
        if not which(tool):
            raise SystemExit(
                "{} not found in the system!".format(tool))

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('input_file')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        raise SystemExit(
            "{} doesn't look like a valid input file!".format(args.input_file))

    target_dir = os.environ.get('C4PS4_TARGET', os.curdir)
    if not os.path.isdir(target_dir):
        raise SystemExit(
            "{} doesn't look like a good target directory!".format(target_dir))
    base, ext = os.path.splitext(args.input_file)
    target_dir = os.environ.get('C4PS4_TARGET', '')
    output_path = os.path.join(
        target_dir, os.path.basename(base) + '_converted_' + ext)

    v, a = strategize(args.input_file)
    if v[1]:  # have to transcode video
        v_codec = 'libx264'
        v_opts = []
    else:
        v_codec = 'copy'
        v_opts = []
    if a[1]:
        a_codec = 'aac'
        a_opts = ['-ac', '2', '-ab', '192k']
    else:
        a_codec = 'copy'
        a_opts = []

    stream_map = ['-map', '0:{}'.format(v[0]), '-map', '0:{}'.format(a[0])]

    # generate ffmpeg invocation
    cmd = ['ffmpeg', '-i', args.input_file]
    cmd += stream_map
    cmd += ['-vcodec', v_codec] + v_opts + ['-acodec', a_codec] + a_opts
    cmd += [output_path]
    if args.dry_run:
        print(" ".join(cmd))
    else:
        subprocess.run(cmd)


def strategize(media_file):
    """Pick the streams to use and determine if they require transcoding."""
    cmd = ['ffprobe', '-print_format', 'json', '-v', 'quiet', '-show_format',
           '-show_streams', media_file]
    output = subprocess.check_output(cmd).decode(sys.stdout.encoding)
    info = json.loads(output)
    audio_candidates = []
    video_stream = -1
    video_conversion = None
    for stream in info['streams']:
        if stream['codec_type'] == 'video':
            # print('Found video stream: #{}, codec: {}'.format(
                # stream['index'], stream['codec_name']))
            if stream['codec_name'] in ALLOWED_VCODECS:
                video_stream = stream['index']
                video_conversion = False
                continue
        if stream['codec_type'] == 'audio':
            # print('Found audio stream: #{}, codec: {}'.format(
                # stream['index'], stream['codec_name']))
            audio_candidates.append(stream)

    def is_in_english(stream):
        return stream['tags'].get('language', '') in ['eng', 'english']
    english_streams = [ac for ac in audio_candidates if is_in_english(ac)]
    if english_streams:
        audio_candidates = english_streams
    # is there a stereo track?
    stereo_streams = [s for s in audio_candidates if
                      s['channel_layout'] == 'stereo']
    if stereo_streams:
        audio_candidates = stereo_streams
    if not audio_candidates:
        print("No suitable audio stream found\n\n")
        from pprint import pprint
        pprint(info['format'])
        raise SystemExit(1)
    good_encoding_streams = [s for s in audio_candidates if
                             s['codec_name'] in ALLOWED_ACODECS]
    if good_encoding_streams:
        audio_stream = good_encoding_streams[0]['index']
        audio_conversion = False  # doesn't need conversion
    else:
        audio_stream = audio_candidates[0]['index']
        audio_conversion = True

    return (
        (video_stream, video_conversion),
        (audio_stream, audio_conversion),
    )


if __name__ == '__main__':
    main()
