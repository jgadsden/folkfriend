import argparse

import imageio
import numpy as np
from folkfriend import ff_config
from folkfriend.data import abc
from folkfriend.decoder import decoder
from folkfriend.sig_proc import spectrogram
from scipy.io import wavfile


def main(path):
    img_path = path.replace('.wav', '.png')
    sample_rate, signal = wavfile.read(path)

    assert sample_rate == ff_config.SAMPLE_RATE

    ac_spec = spectrogram.compute_ac_spectrogram(signal)
    linear_ac_spec = spectrogram.linearise_ac_spectrogram(ac_spec)
    norm_and_save_png(img_path.replace('.png', '-a.png'), linear_ac_spec.T)

    pitch_spec = spectrogram.detect_pitches(linear_ac_spec)
    norm_and_save_png(img_path.replace('.png', '-b.png'), pitch_spec.T)

    onset_spec = spectrogram.detect_onsets(pitch_spec)
    norm_and_save_png(img_path.replace('.png', '-c.png'), onset_spec.T)

    fixed_octaves = spectrogram.fix_octaves(onset_spec)
    norm_and_save_png(img_path.replace('.png', '-d.png'), fixed_octaves.T)

    noise_cleaned = spectrogram.clean_noise(fixed_octaves)
    norm_and_save_png(img_path.replace('.png', '-e.png'), noise_cleaned.T)

    # Spectrogram -> sequence of notes
    contour = decoder.decode(noise_cleaned)

    rendered_contour = decoder.render_contour(contour)
    norm_and_save_png(img_path.replace('.png', '-f.png'), rendered_contour.T)
    
    midi_seq = decoder.contour_to_midi_seq(contour)
    abc_str = abc.midi_seq_to_abc(midi_seq)
    print(abc_str)


def norm_and_save_png(path, img):
    print(f'Writing {path}')
    img = np.asarray(img, dtype=np.float32)
    img -= np.min(img)
    img /= np.max(img)
    img *= 255.0
    img = np.asarray(img, dtype=np.uint8)
    imageio.imwrite(path, img)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'path', help='Path to .wav audio file to debug')
    args = parser.parse_args()
    main(args.path)