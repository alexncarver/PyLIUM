#     Copyright (C) 2015  Alex Carver
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

import os
import subprocess
import re

from natsort import natsorted, ns


def diarize(fp_aud_file, silence=False, marker=None):
        """Input the full path to a wav audio file and this will create result audio files
        from it into the different LIUM assigned speakers; silence is a boolean, default at false,
        which if set to true will pad the result files with silence to synch them time-wise with
        the source file, whilst if marker is given the full path to an audio file it will insert it
        between each audio segment. Both marker and silence cannot be enabled."""
        
        if not fp_aud_file.endswith('.wav'):
                raise(Exception('Requires wav file'))
        if silence and marker:
            raise(Exception('Cannot combine silence padding and marker'))
        print("Creating segments with LIUM, this will take a few minutes...")
        folder, aud_file, seg_file = make_segs(fp_aud_file)
        print("Splitting source audio into segments...")
        speakers = splitter(folder, aud_file, seg_file, silence)
        print("Combining segments into " + str(len(speakers)) + " result files...")
        for speaker in speakers:
                sox_concat(folder, speaker, silence, marker)
        print("All done!")
        return

def make_segs(fp_aud_file):
        """Runs LIUM and creates seg file for input audio."""
        folder, aud_file = os.path.split(fp_aud_file)
        s = ['java', '-Xmx1024m', '-jar', 'C:\Program Files (x86)\sox-14-4-2\LIUM_SpkDiarization-8.4.1.jar', '--fInputMask=' + fp_aud_file,
             '--sOutputMask=' + fp_aud_file[:-3] + 'seg', '--doCEClustering',  aud_file[:-4]]
        subprocess.call(s, shell=True)
        seg_file = aud_file[:-3] + 'seg'
        return folder, aud_file, seg_file

def splitter(folder, aud_file, seg_file, silence=False):
    """Creates individual segment audio files using SoX from source audio and seg file.
        If silence is set to true, pads segment audio with silence to synch with source time."""
        
    aud_file = os.path.join(folder, aud_file)
    seg_file = os.path.join(folder, seg_file)
    speakers = {}
    segs = open(seg_file, 'r')
    for line in segs:
        if line.startswith(';;'):
            continue
        data = line.split(' ')
        if data[-1].endswith('\n'):
            data[-1] = data[-1][:-1]
        start = float(data[2]) / 100
        end = float(data[3]) / 100
        speaker = data[-1]
        if speaker in speakers:
            speakers[speaker] += 1
        else:
            speakers[speaker] = 1
        name = os.path.join(folder, speaker + "-" + str(speakers[speaker]) + ".wav")
        if silence:
            s = ['sox', aud_file, name, 'trim', str(start), str(end), 'pad', str(start), '0']
        else:
            s = ['sox', aud_file, name, 'trim', str(start), str(end)]
        subprocess.call(s, shell=True)
    segs.close()
    return(list(speakers.keys()))

def sox_concat(folder, speaker, silence=False, marker=None):
        """Concatenates segment audio into one result file per speaker. If silence is true, merges instead
        (as segmented audio is already padded by splitter to correct time). If a marker audio file is given,
        this is added between audio segments in the result."""
        regex = r"^" + speaker + r"-[0-9]+.wav$"
        sl = [os.path.join(folder, x ) for x in natsorted(os.listdir(folder),alg=ns.IGNORECASE) if re.match(regex, x)]
        if silence:
            s = ['sox', '-m'] + sl + [os.path.join(folder, 'Result-' + speaker + '.wav'), 'norm']
        else:
            if marker:
                sl = intersperse(sl, marker)
            s = ['sox'] + sl + [os.path.join(folder, 'Result-' + speaker + '.wav'), 'norm']
        subprocess.call(s, shell=True)
        return

def intersperse(lst, item):
    """Intersperses item into list, used to add in marker audio if given."""
    result = [item] * (len(lst) * 2 - 1)
    result[0::2] = lst
    return result
