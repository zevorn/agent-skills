# SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from pedalboard import (Compressor, HighpassFilter, HighShelfFilter, Limiter, LowShelfFilter, Pedalboard,
                        PeakFilter)
import pyloudnorm
from scipy.signal import resample_poly
import soundfile

DESCRIPTION = ('Mix and master the soundtrack: section level rides, optional narration with music ducking, optional '
               'effects stem, glue EQ and compression, loudness normalisation and a true-peak ceiling.')


def load(path: Path, rate: int, length: int | None) -> np.ndarray:
    audio, source_rate = soundfile.read(path, dtype='float64', always_2d=True)
    if source_rate != rate:
        raise SystemExit(f'{path} is {source_rate} Hz; resample it to {rate} Hz first')
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if length is None:
        return audio
    out = np.zeros((length, 2))
    out[:min(length, len(audio))] = audio[:length]
    return out


def true_peak_db(audio: np.ndarray) -> float:
    return float(20 * np.log10(np.max(np.abs(resample_poly(audio, 4, 1, axis=0))) + 1e-12))


def loudness(meter: pyloudnorm.Meter, audio: np.ndarray) -> float:
    return float(meter.integrated_loudness(audio))


def rides(plan: dict | None, length: int, rate: int) -> np.ndarray:
    if not plan:
        return np.ones(length)
    points = [(section['start'], section.get('level', 0.0)) for section in plan['sections']]
    last = plan['sections'][-1]
    points.append((last['end'], last.get('level', 0.0)))
    times, gains = zip(*sorted(points))
    return 10 ** (np.interp(np.arange(length) / rate, times, gains) / 20)


def duck_envelope(voice: np.ndarray, rate: int, depth_db: float, attack: float = .06, release: float = .45) -> np.ndarray:
    hop = int(.01 * rate)
    frames = len(voice) // hop
    rms = np.sqrt(np.mean(voice[:frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    active = (20 * np.log10(rms) > -45).astype(float)
    env = np.zeros(frames)
    up, down = np.exp(-.01 / attack), np.exp(-.01 / release)
    for k in range(frames):
        previous = env[k - 1] if k else 0.0
        coefficient = up if active[k] > previous else down
        env[k] = coefficient * previous + (1 - coefficient) * active[k]
    gain = np.repeat(10 ** (depth_db * env / 20), hop)
    return np.concatenate([gain, np.full(len(voice) - len(gain), gain[-1] if len(gain) else 1.0)])


def master(args) -> dict:
    plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else None
    info = soundfile.info(args.music)
    rate = info.samplerate
    duration = args.duration or (plan['duration'] if plan else info.duration)
    length = int(round(duration * rate))
    meter = pyloudnorm.Meter(rate)
    music = load(args.music, rate, length) * rides(plan, length, rate)[:, None]
    music *= 10 ** ((-20 - loudness(meter, music)) / 20)
    glue = Pedalboard([HighpassFilter(30), LowShelfFilter(cutoff_frequency_hz=110, gain_db=args.low_shelf),
                       PeakFilter(cutoff_frequency_hz=380, gain_db=-1.5, q=.9),
                       HighShelfFilter(cutoff_frequency_hz=7000, gain_db=args.high_shelf),
                       Compressor(threshold_db=-24, ratio=2.2, attack_ms=25, release_ms=220)])
    music = glue(music.T.astype(np.float32), rate).T.astype(np.float64)
    mix = music
    report = {}
    if args.voice:
        voice = load(args.voice, rate, length).mean(axis=1)
        chain = Pedalboard([HighpassFilter(75), PeakFilter(cutoff_frequency_hz=3200, gain_db=2.0, q=.8),
                            Compressor(threshold_db=-22, ratio=3, attack_ms=5, release_ms=80)])
        voice = chain(voice.astype(np.float32)[None, :], rate)[0].astype(np.float64)
        voice *= 10 ** ((-16.0 - loudness(meter, voice)) / 20)
        music *= 10 ** ((-16.5 - loudness(meter, music)) / 20)
        mix = np.stack([voice, voice], axis=1) + music * duck_envelope(voice, rate, args.duck)[:, None]
        report['ducking_db'] = args.duck
    if args.sfx:
        sfx = load(args.sfx, rate, length)
        sfx *= 10 ** ((args.sfx_lufs - loudness(meter, sfx)) / 20)
        mix = mix + sfx
    fade_in, fade_out = int(.01 * rate), int(args.fade_out * rate)
    for depth in np.arange(1.0, 9.5, .5):
        limited = Limiter(threshold_db=-depth, release_ms=120)(mix.T.astype(np.float32), rate).T.astype(np.float64)
        limited[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        if fade_out:
            limited[-fade_out:] *= (np.cos(np.linspace(0, np.pi, fade_out)) * .5 + .5)[:, None]
        limited *= 10 ** ((args.target - loudness(meter, limited)) / 20)
        if true_peak_db(limited) <= args.ceiling:
            break
    else:
        raise SystemExit('the limiter could not reach the true-peak ceiling; lower --target')
    soundfile.write(args.output, limited, rate, subtype='PCM_24')
    report.update({'output': str(args.output), 'lufs': round(loudness(meter, limited), 2),
                   'true_peak_db': round(true_peak_db(limited), 2), 'limiter_depth_db': float(depth),
                   'duration_s': length / rate, 'rate': rate})
    if plan:
        report['section_lufs'] = {section.get('name', f'{section["start"]:g}s'): round(loudness(
            meter, limited[int(section['start'] * rate):int(section['end'] * rate)]), 1)
            for section in plan['sections'] if section['end'] - section['start'] >= .5}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('music', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plan', type=Path, help='music plan; section "level" values (dB) become fader rides')
    parser.add_argument('--voice', type=Path, help='full-length narration track')
    parser.add_argument('--sfx', type=Path, help='full-length effects stem')
    parser.add_argument('--sfx-lufs', type=float, default=-24.0)
    parser.add_argument('--duck', type=float, default=-10.5, help='music gain under narration, dB')
    parser.add_argument('--target', type=float, default=-15.0, help='integrated loudness, LUFS')
    parser.add_argument('--ceiling', type=float, default=-1.5, help='true peak, dBTP')
    parser.add_argument('--duration', type=float)
    parser.add_argument('--fade-out', type=float, default=1.6)
    parser.add_argument('--low-shelf', type=float, default=-2.0)
    parser.add_argument('--high-shelf', type=float, default=1.2)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = master(args)
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.report:
        args.report.write_text(text + '\n', encoding='utf-8')
    sys.stdout.write(text + '\n')


if __name__ == '__main__':
    main()
