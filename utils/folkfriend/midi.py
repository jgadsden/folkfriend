import csv
import math

import numpy as np
from folkfriend import ff_config


class CSVMidiNoteReader(csv.DictReader):
    def __init__(self, *posargs, **kwargs):
        kwargs['fieldnames'] = ['track', 'time', 'type', 'channel',
                                'note', 'velocity']
        super().__init__(*posargs, **kwargs)
        self._notes = self.to_notes()

    def to_pseudo_spectrogram(self, tempo, start_seconds, end_seconds=10):
        sample_seconds = (end_seconds - start_seconds)
        num_frames = ((ff_config.SAMPLE_RATE * sample_seconds
                       ) // ff_config.SPECTROGRAM_HOP_SIZE) - 1
        num_bins = ff_config.NUM_BINS

        # Length in seconds of one frame
        frame_length_s = ff_config.SPECTROGRAM_HOP_SIZE / ff_config.SAMPLE_RATE

        # Times in seconds of frames, after the start point
        frame_times_s = frame_length_s * np.arange(num_frames)

        # Times in seconds of frames thresholds, after the start point.
        #   There's an extra half here for centering.
        frame_times_s += frame_length_s / 2

        # Add start offset
        frame_times_s += start_seconds

        # Convert to milliseconds
        frame_times_ms = 1000 * frame_times_s

        pseudo_spectrogram = np.zeros((num_frames, num_bins), dtype=np.uint8)

        for note in self._notes:
            note.set_tempo(tempo)

            # Note occurs outwith range specified
            if note.end < 1000 * start_seconds or note.start > 1000 * end_seconds:
                continue

            # Get the first and last frames of this note
            start_frame = np.argmax(frame_times_ms > note.start)
            end_frame = np.argmax(frame_times_ms > note.end)

            if note.start < frame_times_ms[-1] < note.end:
                # RHS edge case
                end_frame = num_frames  # Clip to end

            if note.start < frame_times_ms[0] < note.end:
                # LHS edge case
                start_frame = 0     # Clip to start

            # not required?
            # if end_frame <= start_frame:
                # argmax can return 0 if no matches. Skip this note.
                # continue

            # Invalid note. Skip this note.
            if not ff_config.LOW_MIDI < note.pitch < ff_config.HIGH_MIDI:
                continue

            # -1 because inclusive range. The linear midi bins go
            #   [102.   101.8   101.6   ...     46.6.   46.4    46.2]
            lo_index = (math.ceil(ff_config.BINS_PER_MIDI / 2)
                        + ff_config.BINS_PER_MIDI
                        * (ff_config.HIGH_MIDI - 1 - note.pitch))
            hi_index = lo_index + ff_config.BINS_PER_MIDI
            pseudo_spectrogram[start_frame: end_frame, lo_index: hi_index] = 255

        return pseudo_spectrogram

    def to_notes(self):
        """Convert these midi instructions to a list of Note objects"""

        active_notes = {}
        notes = []

        for record in self:
            if not record['note'] or not record['note'].isdigit():
                continue
            note = int(record['note'])
            time = int(record['time'])

            if record['type'] == 'Note_on_c':
                if note not in active_notes:
                    active_notes[note] = time
            elif record['type'] == 'Note_off_c':
                if note not in active_notes:
                    continue

                note_end = time
                note_start = active_notes.pop(note)

                notes.append(Note(start=note_start,
                                  end=note_end,
                                  pitch=note))

        return notes

    def to_note_contour(self, tempo, start_seconds, end_seconds=10):
        label = ''

        for record in self:
            raise NotImplementedError()

        return label


class Note:
    def __init__(self, start, end, pitch):
        """Store a single note.

        All times are in milliseconds unless otherwise stated."""
        self._midi_start = start
        self._midi_end = end
        self.pitch = pitch

        self.start = self._midi_start
        self.end = self._midi_end

    def set_tempo(self, tempo):
        # Tempo specified in crotchet beats per minute
        us_per_crotchet = 60000000. / tempo

        # Beware that abc2midi does not adjust tempo by changing the times at
        #   which notes start or end, but by (sensibly) passing the tempo to
        #   the midi file itself which has a command to set the tempo, which
        #   must be interpreted by whatever reads the midi file (eg fluidsynth
        #   and this script).

        # This 480,000 comes from 125 bpm being the default tempo with the hard
        #   coded midi times (240ms = 1 quaver => 480000us = 1 crotchet).
        ms_scale_factor = us_per_crotchet / 480000

        self.start = ms_scale_factor * self._midi_start
        self.end = ms_scale_factor * self._midi_end

    @property
    def duration(self):
        return self.end - self.start


class ABCHandler:
    def __init__(self):
        pass

    @staticmethod
    def expand_abc(tune):
        """Given an ABC string, return a list abc-style notes all as quavers"""

        music_time = 0
        output_time = 0
        output_pitches = []

        for i, note in enumerate(notes):
            music_time += note.duration

            # If we're ahead, skip notes until we're back in sync
            if music_time <= output_time:
                continue

            if note.duration.is_integer():
                output_time += note.duration
                output_pitches.extend([note.pitch.abs_value] *
                                      int(note.duration))
            elif note.duration < 1.0:
                output_time += 1.0
                output_pitches.append(note.pitch.abs_value)
            else:
                # If we've fallen behind, round up, else round down
                round_f = math.ceil if music_time > output_time else math.floor

                rounded_int = round_f(note.duration)
                output_time += rounded_int
                output_pitches.extend([note.pitch.abs_value] *
                                      int(note.duration))

        return output_pitches
