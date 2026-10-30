# SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pretty_midi
from pychord import Chord

DESCRIPTION = ('Write a Csound score from a music plan (sections, chords, layers, hits, cues) and render it with '
               'assets/music/promo.orc. See references/audio.md for the plan format.')
SKILL = Path(__file__).resolve().parents[1]
ORCHESTRA = SKILL / 'assets/music/promo.orc'
ARP_ORDER = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 3, 5, 4, 3, 2, 1]
DEFAULT_SCALE = ['D', 'F', 'G', 'A', 'C']


def hz(note: str) -> float:
    return pretty_midi.note_number_to_hz(pretty_midi.note_name_to_number(note))


def midi(note: str) -> int:
    return pretty_midi.note_name_to_number(note)


def voicing(symbol: str) -> dict:
    tones = Chord(symbol).components_with_pitch(root_pitch=3)
    root = Chord(symbol).root
    bass_octave = 1 if midi(f'{root}2') > midi('F2') else 2
    upper = [pretty_midi.note_number_to_name(midi(tone) + 12) for tone in tones]
    pad = tones + [upper[1 if len(upper) > 1 else 0]]
    arp = (upper + [pretty_midi.note_number_to_name(midi(tone) + 12) for tone in upper])[:6]
    while len(arp) < 6:
        arp.append(arp[len(arp) % len(upper)])
    return {'pad': pad, 'bass': f'{root}{bass_octave}', 'arp': arp}


def snap_to_scale(freq: float, scale: list[str]) -> float:
    classes = {pretty_midi.note_name_to_number(f'{name}4') % 12 for name in scale}
    target = pretty_midi.hz_to_note_number(max(freq, 30.0))
    candidates = [n for n in range(24, 108) if n % 12 in classes]
    return pretty_midi.note_number_to_hz(min(candidates, key=lambda n: abs(n - target)))


class Score:
    def __init__(self, bpm: float):
        self.lines: list[str] = []
        self.beat = 60 / bpm
        self.bar = self.beat * 4
        self.step = self.beat / 4

    def event(self, instrument: int, start: float, duration: float, *fields: float) -> None:
        values = ' '.join(f'{value:.6g}' for value in fields)
        self.lines.append(f'i {instrument} {start:.4f} {duration:.4f} {values}'.rstrip())

    def pad(self, chord: dict, start: float, duration: float, amp: float, cutoff: float, duck: float,
            attack: float, release: float) -> None:
        for index, note in enumerate(chord['pad']):
            self.event(12, start, duration, hz(note), amp * (1.15 if index == 0 else 1), cutoff, duck, attack, release)

    def bass(self, chord: dict, start: float, end: float, amp: float, cutoff: float, duck: float) -> None:
        root = hz(chord['bass'])
        steps = int(round((end - start) / (self.beat / 2)))
        for step in range(steps):
            freq = root * (2 if step % 8 == 7 else 1)
            self.event(10, start + step * self.beat / 2, self.beat / 2 * .82, freq,
                       amp * (1 if step % 4 == 0 else .78), cutoff, duck)

    def arp(self, chord: dict, start: float, end: float, amp: float, brightness: float, octave: float,
            order: list[int]) -> None:
        steps = int(round((end - start) / self.step))
        for step in range(steps):
            note = hz(chord['arp'][order[step % len(order)]]) * octave
            self.event(11, start + step * self.step, .2, note, amp * (1 if step % 4 == 0 else .82),
                       .32 if step % 2 == 0 else .68, brightness)

    def drums(self, start: float, end: float, layers: dict, hats_mode: str, duck: float) -> None:
        beats = int(round((end - start) / self.beat))
        for beat in range(beats):
            time = start + beat * self.beat
            if layers.get('kick'):
                self.event(4, time, .45, layers['kick'])
                self.event(3, time, self.beat * .9, duck)
            if layers.get('clap') and beat % 2 == 1:
                self.event(21, time, .32, layers['clap'])
        if layers.get('hats'):
            for step in range(beats * 4):
                offbeat = step % 4 == 2
                if hats_mode == 'eighth' and not offbeat:
                    continue
                decay = .09 if offbeat and hats_mode == 'eighth' else .045
                self.event(20, start + step * self.step, decay + .05, layers['hats'] * (1 if offbeat else .55), decay,
                           .42 if step % 2 else .58)

    def ticks(self, start: float, end: float, amp: float, freq: float, every: float) -> None:
        for step in range(int(round((end - start) / every))):
            accent = step % 4 == 0
            self.event(22, start + step * every, .05, amp * (1.35 if accent else 1), freq * (1.25 if accent else 1),
                       .4 if step % 2 else .6)

    def hit(self, time: float, amp: float, shimmer: float) -> None:
        self.event(30, time, 3.2, amp, shimmer)
        self.event(33, time, 1.6, amp * .16)

    def bell(self, time: float, freq: float, amp: float, duration: float = 1.6, pan: float = .5,
             ratio: float = 1.0, index: float = 1.4) -> None:
        self.event(13, time, duration, freq, amp, pan, ratio, index)

    def chime(self, time: float, bright: bool) -> None:
        if bright:
            self.bell(time, hz('D6'), .11, 1.4, .58, 2.0, 1.6)
            self.bell(time + .09, hz('A6'), .09, 1.6, .62, 2.0, 1.4)
        else:
            self.bell(time, hz('A5'), .065, 1.2, .4, 2.0, 1.0)


def section_chords(section: dict, bar: float) -> list[tuple[float, float, dict]]:
    span = section.get('bars_per_chord', 2) * bar
    chords = section.get('chords', [])
    if not chords:
        return []
    result = []
    time, index = section['start'], 0
    while time < section['end'] - 1e-6:
        end = min(section['end'], time + span)
        result.append((time, end, voicing(chords[index % len(chords)])))
        time, index = end, index + 1
    return result


def compose(plan: dict) -> Score:
    score = Score(plan['bpm'])
    duration = plan['duration']
    tail = plan.get('tail', 6)
    score.event(2, 0, duration + tail)
    score.event(98, 0, duration + tail, score.beat * 1.5, plan.get('delay_feedback', .38))
    score.event(99, 0, duration + tail, plan.get('reverb_feedback', .87), plan.get('reverb_level', .62))
    for section in plan['sections']:
        layers = section.get('layers', {})
        drums = bool(layers.get('kick'))
        duck = section.get('duck', .45 if drums else 0.0)
        for start, end, chord in section_chords(section, score.bar):
            length = end - start
            if layers.get('pad'):
                score.pad(chord, start, length + .2, layers['pad'], section.get('cutoff', 2200), duck,
                          section.get('attack', .6 if length >= 4 else .25), section.get('release', 1.8 if length >= 4 else .8))
            if layers.get('bass'):
                score.bass(chord, start, end, layers['bass'], section.get('bass_cutoff', 700), .55 if drums else 0.0)
            if layers.get('arp'):
                score.arp(chord, start, end, layers['arp'], section.get('brightness', .55),
                          section.get('arp_octave', 1), ARP_ORDER)
            if layers.get('arp_high'):
                score.arp(chord, start, end, layers['arp_high'], section.get('brightness', .55) + .1, 2, ARP_ORDER[::-1])
        if layers.get('drone'):
            first = section_chords(section, score.bar)
            root = hz(first[0][2]['bass']) if first else hz(section.get('drone_note', 'D2'))
            root = root * 2 if root < 65 else root
            score.event(14, section['start'], section['end'] - section['start'], root, layers['drone'],
                        section.get('drone_attack', 1.5), section.get('drone_release', .6), section.get('drone_cutoff', 900))
        if drums or layers.get('clap') or layers.get('hats'):
            score.drums(section['start'], section['end'], layers, section.get('hats_mode', 'eighth'), 1.0)
        if layers.get('ticks'):
            score.ticks(section['start'], section['end'], layers['ticks'], section.get('ticks_freq', 3000),
                        section.get('ticks_every', score.step))
    for item in plan.get('hits', []):
        score.hit(item['t'], item.get('amp', .8), item.get('shimmer', .5))
    for item in plan.get('risers', []):
        score.event(31, item['end'] - item['duration'], item['duration'], item.get('amp', .25), 110, 440)
    for item in plan.get('swells', []):
        for note in voicing(item['chord'])['pad'][1:4]:
            score.event(32, item['end'] - item['duration'], item['duration'], hz(note), item.get('amp', .12))
    for item in plan.get('rolls', []):
        count = int(round(item['duration'] / score.step))
        for step in range(count):
            level = item.get('low', .05) + (item.get('high', .4) - item.get('low', .05)) * (step / max(1, count - 1)) ** 1.6
            score.event(21, item['start'] + step * score.step, .25, level)
    for item in plan.get('thuds', []):
        score.event(34, item['t'], .5, item.get('amp', .8))
    for item in plan.get('bells', []):
        score.bell(item['t'], hz(item['note']), item.get('amp', .1), item.get('duration', 1.6), item.get('pan', .5),
                   item.get('ratio', 1.0), item.get('index', 1.4))
    for item in plan.get('chimes', []):
        score.chime(item['t'], item.get('bright', True))
    return score


def merge_cues(plan: dict, cues: list[dict]) -> None:
    # Page cue types map onto score events, so a getCues() export can drive the effects directly.
    scale = plan.get('scale', DEFAULT_SCALE)
    for cue in cues:
        kind, time = cue['type'], cue['t']
        if kind == 'impact':
            plan.setdefault('hits', []).append({'t': time, 'amp': .8 * cue.get('size', 1.0), 'shimmer': .5})
        elif kind == 'thud':
            plan.setdefault('thuds', []).append({'t': time, 'amp': cue.get('amp', .8)})
        elif kind == 'chime':
            plan.setdefault('chimes', []).append({'t': time, 'bright': cue.get('bright', True)})
        elif kind == 'blip':
            freq = snap_to_scale(cue.get('pitch', 2000.0), scale)
            plan.setdefault('bells', []).append({'t': time, 'note': pretty_midi.note_number_to_name(
                round(pretty_midi.hz_to_note_number(freq))), 'amp': .08, 'duration': 1.0, 'ratio': 3.5, 'index': 1.2})
        elif kind == 'riser':
            plan.setdefault('risers', []).append({'end': time, 'duration': cue.get('dur', 3.0), 'amp': cue.get('amp', .25)})
        elif kind == 'transition':
            continue
        else:
            print(f'cue type {kind!r} at {time} s has no score mapping; skipped', file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('plan', type=Path, help='music plan JSON')
    parser.add_argument('output', type=Path, help='rendered float WAV')
    parser.add_argument('--cues', type=Path, help='JSON list of page cues, or an object with a "cues" list')
    parser.add_argument('--orchestra', type=Path, default=ORCHESTRA)
    parser.add_argument('--score', type=Path, help='where to keep the generated .sco (default: beside the output)')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    if args.cues:
        data = json.loads(args.cues.read_text(encoding='utf-8'))
        merge_cues(plan, data['cues'] if isinstance(data, dict) else data)
    bar = 240 / plan['bpm']
    for section in plan['sections']:
        offset = section['start'] / bar
        if not math.isclose(offset, round(offset), abs_tol=1e-3):
            print(f'section at {section["start"]} s starts {offset:.3f} bars in; snap it with tempo_grid.py', file=sys.stderr)
    score = compose(plan)
    score_path = args.score or args.output.with_suffix('.sco')
    score_path.write_text('\n'.join(score.lines) + '\ne\n', encoding='utf-8')
    csound = shutil.which('csound')
    if csound is None:
        raise SystemExit('csound is required (brew install csound / apt install csound)')
    subprocess.run([csound, '-d', '-W', '-f', '-m0', '-o', str(args.output), str(args.orchestra), str(score_path)], check=True)
    print(f'{len(score.lines)} events -> {args.output} (score {score_path})')


if __name__ == '__main__':
    main()
