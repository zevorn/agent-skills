; SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
; SPDX-License-Identifier: MIT
; Instruments for scripts/compose_music.py. Instrument numbers and p-fields are part of the score contract.

sr = 48000
ksmps = 16
nchnls = 2
0dbfs = 1

gaRevL init 0
gaRevR init 0
gaDelL init 0
gaDelR init 0
gkDuck init 0
giSine ftgen 1, 0, 16384, 10, 1

; Sidechain value: cleared every control cycle, then raised by duck events.
instr 2
  gkDuck = 0
endin

; Duck event: p4 depth
instr 3
  kenv expseg 1, p3, 0.001
  gkDuck = max(gkDuck, kenv * p4)
endin

; Kick: p4 amp
instr 4
  kpitch expseg 170, 0.035, 62, 0.2, 44, 0.3, 40
  aenv expseg 1, 0.34, 0.0005
  abody poscil 1, kpitch, giSine
  aclickenv expseg 1, 0.006, 0.0005
  anoise rand 1
  aclick butterhp anoise * aclickenv, 3500
  aout = (tanh(abody * aenv * 1.5) * 0.85 + aclick * 0.45) * p4 * 0.8
  outs aout, aout
endin

; Bass: p4 freq, p5 amp, p6 cutoff, p7 duck depth
instr 10
  aenv madsr 0.004, 0.12, 0.7, 0.06
  kcut expseg p6 * 4, 0.09, p6, p3, p6 * 0.9
  asaw vco2 1, p4
  asq vco2 0.6, p4 * 1.003, 10
  asub poscil 1, p4, giSine
  afilt moogladder (asaw + asq) * 0.5, kcut, 0.25
  aout = (afilt * 0.75 + asub * 0.32) * aenv * p5 * 0.62 * (1 - gkDuck * p7)
  outs aout, aout
endin

; Pluck: p4 freq, p5 amp, p6 pan, p7 brightness 0..1
instr 11
  aenv expseg 0.001, 0.004, 1, p3 - 0.004, 0.001
  kcut expseg 500 + p7 * 5200, 0.16, 320 + p7 * 900, p3, 260
  a1 vco2 0.5, p4
  a2 vco2 0.45, p4 * 1.006, 10
  af moogladder a1 + a2, kcut, 0.22
  aout = af * aenv * p5 * 1.5 * (1 - gkDuck * 0.3)
  aL, aR pan2 aout, p6
  outs aL, aR
  gaDelL = gaDelL + aL * 0.32
  gaDelR = gaDelR + aR * 0.32
  gaRevL = gaRevL + aL * 0.18
  gaRevR = gaRevR + aR * 0.18
endin

; Pad: p4 freq, p5 amp, p6 cutoff, p7 duck depth, p8 attack, p9 release
instr 12
  aenv linsegr 0, p8, 1, p9, 0
  irate random 0.07, 0.14
  iphase random 0, 1
  klfo poscil 1, irate, giSine, iphase
  kcut = p6 * (1 + 0.22 * klfo)
  a1 vco2 1, p4 * 0.9962
  a2 vco2 1, p4 * 1.0041
  a3 vco2 1, p4 * 1.0016
  a4 vco2 1, p4 * 0.9983
  aL moogladder a1 + a3 * 0.7, kcut, 0.12
  aR moogladder a2 + a4 * 0.7, kcut, 0.12
  aL butterhp aL, 150
  aR butterhp aR, 150
  kduck = 1 - gkDuck * p7
  aL = aL * aenv * p5 * kduck * 0.6
  aR = aR * aenv * p5 * kduck * 0.6
  outs aL, aR
  gaRevL = gaRevL + aL * 0.5
  gaRevR = gaRevR + aR * 0.5
endin

; FM bell: p4 freq, p5 amp, p6 pan, p7 modulator ratio, p8 index
instr 13
  kidx expseg p8, p3, 0.15
  aenv expseg 0.001, 0.004, 1, p3 - 0.004, 0.0005
  a1 foscili aenv, p4, 1, p7, kidx, giSine
  a2 poscil aenv * 0.25, p4 * 2.001, giSine
  aout = (a1 + a2) * p5 * 1.2
  aL, aR pan2 aout, p6
  outs aL, aR
  gaDelL = gaDelL + aL * 0.3
  gaDelR = gaDelR + aR * 0.3
  gaRevL = gaRevL + aL * 0.55
  gaRevR = gaRevR + aR * 0.55
endin

; Drone: p4 freq, p5 amp, p6 attack, p7 release, p8 final cutoff
instr 14
  aenv linsegr 0, p6, 1, p7, 0
  kcut expseg 140, p3, p8
  klfo poscil 0.15, 0.09, giSine
  a1 vco2 1, p4
  a2 vco2 1, p4 * 1.007
  asub poscil 1, p4 * 0.5, giSine
  af moogladder a1 + a2, kcut * (1 + klfo), 0.3
  aout = (af * 0.45 + asub * 0.3) * aenv * p5
  outs aout, aout
  gaRevL = gaRevL + aout * 0.2
  gaRevR = gaRevR + aout * 0.2
endin

; Hat: p4 amp, p5 decay, p6 pan
instr 20
  aenv expseg 1, p5, 0.0005
  anoise rand 1
  ahp butterhp anoise, 7200
  abp butterbp ahp, 10500, 7000
  aout = abp * aenv * p4 * 1.6
  aL, aR pan2 aout, p6
  outs aL, aR
  gaRevL = gaRevL + aL * 0.06
  gaRevR = gaRevR + aR * 0.06
endin

; Clap: p4 amp
instr 21
  anoise rand 1
  aburst linseg 0, 0.001, 1, 0.008, 0.18, 0.001, 1, 0.008, 0.18, 0.001, 1, 0.19, 0
  atail expseg 0.0001, 0.02, 1, 0.24, 0.0005
  abp butterbp anoise, 1400, 900
  ahp butterhp anoise, 2600
  aout = (abp * aburst * 0.9 + ahp * atail * 0.3) * p4
  outs aout * 0.95, aout
  gaRevL = gaRevL + aout * 0.28
  gaRevR = gaRevR + aout * 0.28
endin

; Tick: p4 amp, p5 freq, p6 pan
instr 22
  aenv expseg 1, 0.03, 0.0005
  a1 poscil aenv * p4, p5, giSine
  aL, aR pan2 a1, p6
  outs aL, aR
  gaRevL = gaRevL + aL * 0.12
  gaRevR = gaRevR + aR * 0.12
endin

; Impact: p4 amp, p5 shimmer amount
instr 30
  kpitch expseg 72, 0.08, 46, 1.8, 26
  aenv expseg 1, p3, 0.0005
  aboom poscil 1, kpitch, giSine
  aboom = tanh(aboom * 1.7) * aenv
  anoise rand 1
  anenv expseg 1, 0.9, 0.0005
  anz butterlp anoise * anenv, 1100
  ashenv expseg 0.0001, 0.01, 1, 2.6, 0.0005
  ash butterhp anoise * ashenv, 6500
  amono = (aboom * 0.85 + anz * 0.3) * p4
  ashL = ash * p5 * p4 * 0.22
  outs amono + ashL, amono + ashL * 0.9
  gaRevL = gaRevL + (amono * 0.3 + ashL * 0.6)
  gaRevR = gaRevR + (amono * 0.3 + ashL * 0.6)
endin

; Riser: p4 amp, p5 start pitch, p6 end pitch
instr 31
  kcf expseg 300, p3, 9000
  kamp expseg 0.01, p3, 1
  kgate linseg 1, p3 - 0.01, 1, 0.01, 0
  anoise rand 1
  abp butterbp anoise, kcf, kcf * 0.6
  kp expseg p5, p3, p6
  asaw vco2 0.3, kp
  asf moogladder asaw, kcf * 0.5, 0.3
  aout = (abp * 0.75 + asf * 0.45) * kamp * kgate * p4
  outs aout * 0.9, aout
  gaRevL = gaRevL + aout * 0.3
  gaRevR = gaRevR + aout * 0.3
endin

; Reverse swell: p4 freq, p5 amp
instr 32
  kamp expseg 0.001, p3 - 0.012, 1, 0.012, 0.001
  kcut expseg 400, p3, 5000
  a1 vco2 1, p4
  a2 vco2 1, p4 * 1.005
  af moogladder a1 + a2, kcut, 0.15
  aout = af * kamp * p5 * 0.5
  outs aout, aout
  gaRevL = gaRevL + aout * 0.35
  gaRevR = gaRevR + aout * 0.35
endin

; Downlifter: p4 amp
instr 33
  kcf expseg 6000, p3, 180
  kamp expseg 1, p3, 0.001
  anoise rand 1
  abp butterbp anoise, kcf, kcf * 0.7
  aout = abp * kamp * p4
  outs aout, aout * 0.92
  gaRevL = gaRevL + aout * 0.3
  gaRevR = gaRevR + aout * 0.3
endin

; Body thud for on-screen collisions: p4 amp
instr 34
  kp expseg 140, 0.09, 52
  aenv expseg 1, 0.24, 0.0005
  a1 poscil 1, kp, giSine
  anoise rand 1
  aknockenv expseg 1, 0.06, 0.0005
  aknock butterbp anoise * aknockenv, 850, 600
  aout = (a1 * aenv * 0.9 + aknock * 0.7) * p4
  outs aout, aout
  gaRevL = gaRevL + aout * 0.15
  gaRevR = gaRevR + aout * 0.15
endin

; Ping-pong delay: p4 time, p5 feedback
instr 98
  afbL init 0
  afbR init 0
  ain = (gaDelL + gaDelR) * 0.5
  abufL delayr 2
  atapL deltapi p4
  delayw ain + afbR
  abufR delayr 2
  atapR deltapi p4
  delayw afbL
  afbL = butterlp(atapL, 4800) * p5
  afbR = butterlp(atapR, 4800) * p5
  outs atapL * 0.55, atapR * 0.55
  gaRevL = gaRevL + atapL * 0.2
  gaRevR = gaRevR + atapR * 0.2
  gaDelL = 0
  gaDelR = 0
endin

; Reverb: p4 feedback, p5 wet level
instr 99
  aL, aR reverbsc gaRevL, gaRevR, p4, 8500
  outs aL * p5, aR * p5
  gaRevL = 0
  gaRevR = 0
endin
