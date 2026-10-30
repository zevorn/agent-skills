# SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pyloudnorm
from scipy.signal import welch
import soundfile

DESCRIPTION = ('Report loudness and the share of energy per frequency band for each section of a mix, and draw a '
               'spectrogram and waveform with FFmpeg. Typical electronic mixes sit near: sub -8, bass -3, '
               'low-mid -7, mid -12, presence -18, air -24 dB of total power.')
BANDS = [(20, 60, 'sub'), (60, 250, 'bass'), (250, 1000, 'low-mid'), (1000, 4000, 'mid'),
         (4000, 10000, 'presence'), (10000, 20000, 'air')]


def bands(audio: np.ndarray, rate: int) -> dict:
    frequencies, power = welch(audio.mean(axis=1), rate, nperseg=8192)
    total = np.trapezoid(power, frequencies)
    result = {}
    for low, high, name in BANDS:
        mask = (frequencies >= low) & (frequencies < high)
        result[name] = round(float(10 * np.log10(np.trapezoid(power[mask], frequencies[mask]) / total + 1e-12)), 1)
    return result


def segments(plan: dict | None, duration: float, every: float | None) -> list[tuple[str, float, float]]:
    if plan:
        return [(s.get('name', f'{s["start"]:g}s'), s['start'], s['end']) for s in plan['sections']]
    step = every or duration
    starts = np.arange(0, duration, step)
    return [(f'{start:g}s', float(start), float(min(duration, start + step))) for start in starts]


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--plan', type=Path, help='music plan whose sections define the segments')
    parser.add_argument('--every', type=float, help='segment length in seconds when no plan is given')
    parser.add_argument('--spectrum', type=Path, help='write a spectrogram PNG')
    parser.add_argument('--wave', type=Path, help='write a waveform PNG')
    parser.add_argument('--json', type=Path, help='write the report as JSON')
    args = parser.parse_args()
    audio, rate = soundfile.read(args.audio, dtype='float64', always_2d=True)
    meter = pyloudnorm.Meter(rate)
    plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else None
    report = {'whole': {'lufs': round(float(meter.integrated_loudness(audio)), 1), **bands(audio, rate)}}
    for name, start, end in segments(plan, len(audio) / rate, args.every):
        chunk = audio[int(start * rate):int(end * rate)]
        if len(chunk) < rate // 2:
            continue
        report[name] = {'lufs': round(float(meter.integrated_loudness(chunk)), 1), **bands(chunk, rate)}
    header = f'{"segment":12}{"LUFS":>8}' + ''.join(f'{band:>10}' for _, _, band in BANDS)
    print(header)
    for name, values in report.items():
        print(f'{name[:12]:12}{values["lufs"]:>8}' + ''.join(f'{values[band]:>10}' for _, _, band in BANDS))
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    ffmpeg = shutil.which('ffmpeg')
    if (args.spectrum or args.wave) and ffmpeg is None:
        sys.exit('ffmpeg is required for --spectrum and --wave')
    if args.spectrum:
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(args.audio), '-lavfi',
                        'showspectrumpic=s=1800x500:mode=combined:scale=log:fscale=log:legend=1', str(args.spectrum)], check=True)
    if args.wave:
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(args.audio), '-lavfi',
                        'showwavespic=s=1800x300:colors=#ec4a22', str(args.wave)], check=True)


if __name__ == '__main__':
    main()
