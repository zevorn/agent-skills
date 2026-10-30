<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission -->
<!-- SPDX-License-Identifier: MIT -->

# 配乐、音效与旁白

## 小节网格

- 速度取整数：120 BPM 时一拍 0.5 s、一小节 2 s，场景起点、重击与段落切换都落在小节线上。
- `scripts/tempo_grid.py --timeline timeline.json --bpm 120 --major title,bridge,close` 给出移到小节网格后的起点与最大偏移；
  移动不超过 1 s 的起点通常不影响内容，移动后重新渲染画面。
- 有旁白时以旁白时长排布场景：每段结束时间向上取整到小节线，富余的小节分给可以拉长的段落。

## 音乐计划

`scripts/compose_music.py plan.json music.wav --cues cues.json` 读取下面的计划，生成 Csound 乐谱，
用 `assets/music/promo.orc` 渲染 48 kHz 32 位浮点 WAV。

```json
{
  "bpm": 120,
  "duration": 168,
  "scale": ["D", "F", "G", "A", "C"],
  "sections": [
    {"name": "open", "start": 0, "end": 6, "chords": ["Dm"], "bars_per_chord": 3, "level": -2,
     "layers": {"drone": 0.18, "ticks": 0.05}},
    {"name": "part3", "start": 98, "end": 158, "chords": ["Dm", "Bb", "F", "C"], "bars_per_chord": 1, "level": 0,
     "layers": {"pad": 0.12, "bass": 0.33, "arp": 0.085, "kick": 0.82, "clap": 0.5, "hats": 0.11},
     "hats_mode": "sixteen", "cutoff": 2600, "brightness": 0.72, "bass_cutoff": 950}
  ],
  "hits": [{"t": 6, "amp": 0.95, "shimmer": 0.55}],
  "risers": [{"end": 6, "duration": 3, "amp": 0.22}],
  "swells": [{"end": 6, "duration": 1.6, "chord": "Dm", "amp": 0.16}],
  "rolls": [{"start": 156, "duration": 2, "low": 0.06, "high": 0.5}],
  "thuds": [{"t": 0.7, "amp": 0.85}],
  "bells": [{"t": 6.5, "note": "A5", "amp": 0.13, "duration": 1.6}],
  "chimes": [{"t": 99.63, "bright": true}]
}
```

| 字段 | 含义 |
| --- | --- |
| `sections[].chords` | 和弦符号（pychord 解析），按 `bars_per_chord` 小节循环 |
| `sections[].layers` | 各声部振幅：`drone`、`pad`、`bass`、`arp`、`arp_high`、`kick`、`clap`、`hats`、`ticks` |
| `sections[].level` | 该段的推子电平（dB），由 `master_audio.py --plan` 在段落之间平滑过渡 |
| `cutoff` / `bass_cutoff` / `brightness` | 铺底滤波、贝斯滤波、琶音亮度（0–1） |
| `duck` | 底鼓对铺底的侧链压缩深度，默认有底鼓时 0.45 |
| `hats_mode` | `eighth`（反拍八分）或 `sixteen`（十六分） |
| `hits` / `risers` / `swells` / `rolls` | 重击、上升音效、反向渐强、军鼓滚奏 |
| `thuds` / `bells` / `chimes` | 撞击声、铃音旋律、成功提示音（`bright` 为明亮版本） |
| `scale` | 页面 `blip` 提示点吸附到的音阶 |

页面提示点的映射：`impact` → 重击，`thud` → 撞击声，`chime` → 提示音，`blip` → 吸附到音阶的短铃音，`riser` → 以该时刻结束的上升音效。

## 和声与段落

- 小调更适合技术产品：i–VI–III–VII（Dm–Bb–F–C）每两小节一换适合讲解段，每小节一换适合实测段；收尾转到同主音大调（D）。
- 进入新段落前一小节放属和弦（A）或上升音效，下一段第一拍放重击。重击前 0.2–0.3 s 把配乐压低几 dB，重击时底鼓、镲片与次低频同时落下，落差更明显。
- 旋律音放在和弦音或九音上；成功提示音（D6 + A6）与当前和弦相容。
- 能量逐段上升：开场与讲解段 −5 至 −2 dB，平台段 −2 至 −1 dB，实测段 0 dB，收尾重击后回落。
- 画面事件对应音效：推力出现配撞击声，“控制就绪”“恢复站立”“完成”配提示音（产品方明亮，基准方柔和），数据画面叠加高频节拍声。

## 旁白

- 文案按句写进脚本 JSON；`edge-tts` 合成时请求 `WordBoundary`，用词边界生成逐字字幕时间；以“音色 | 语速 | 文本”的哈希缓存音频。
- 用 Whisper 转写每句旁白，对照脚本检查读音与多音字。
- `master_audio.py --voice voice.wav` 把旁白单独压到 −16 LUFS，配乐压到 −16.5 LUFS，旁白出现时配乐闪避 10.5 dB。

## 母带与检查

```sh
python3 scripts/master_audio.py music.wav mix.wav --plan plan.json --target -15 --ceiling -1.5
python3 scripts/analyze_audio.py mix.wav --plan plan.json --spectrum spectrum.png --wave wave.png
```

- 响度：无旁白 −15 LUFS，有旁白 −14 LUFS；真峰值不高于 −1.5 dBTP（AAC 编码后约 −1 dBTP）。
- 频段能量占比的参考值：sub −8、bass −3、low-mid −7、mid −12、presence −18、air −24 dB。
  低频过重时降低贝斯的正弦低音层、持续音和重击，铺底加 150 Hz 高通；中高频不足时提高琶音、镲片和铃音，母带高架提升 1–2 dB。
- 波形图应能看出段落起伏；频谱图上重击、上升音效与段落切换的位置应与分镜一致。
- 成片合成后用 `ffmpeg -i film.mp4 -map 0:a -af ebur128=peak=true -f null -` 复核成片响度。
- 智能体无法试听时，以响度、频段占比、频谱图、波形图和音画同步测量作为验收依据，并在交付说明中写明检查方式。

## 其他音色来源

- 钢琴、弦乐、合唱可以用 FluidSynth 渲染 SoundFont（例如 GeneralUser GS），MIDI 由 `pretty_midi` 生成；使用前确认音色库许可。
- 也可以用 NumPy/SciPy 合成并以 Pedalboard 处理效果，结构与本计划一致即可。
