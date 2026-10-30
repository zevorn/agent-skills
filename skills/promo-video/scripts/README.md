<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission -->
<!-- SPDX-License-Identifier: MIT -->

# 脚本参考

所有脚本使用 Python 3.10 或更新版本。安装依赖：

```sh
SKILL_DIR=/path/to/promo-video
python3 -m venv .venv
.venv/bin/pip install -r "$SKILL_DIR/scripts/requirements.txt"
.venv/bin/python -m playwright install chromium
```

外部程序：FFmpeg（全部视频与音频处理）、Csound（`compose_music.py`）、Node.js 与 npm（合成页面模板的字体与 GSAP）。
macOS：`brew install ffmpeg csound node`；Debian / Ubuntu：`apt install ffmpeg csound nodejs npm`。

## render_frames.py

```sh
python3 "$SKILL_DIR/scripts/render_frames.py" snap page/index.html 3 9.5 15 --out snaps
python3 "$SKILL_DIR/scripts/render_frames.py" snap page/index.html --every 2 --out snaps
python3 "$SKILL_DIR/scripts/render_frames.py" eval page/index.html "window.qaText(0, window.DURATION, 0.2)"
python3 "$SKILL_DIR/scripts/render_frames.py" eval page/index.html "window.getCues()" > cues.json
python3 "$SKILL_DIR/scripts/render_frames.py" check page/index.html 2 30 95.5
python3 "$SKILL_DIR/scripts/render_frames.py" subtitles page/index.html out/film.srt
python3 "$SKILL_DIR/scripts/render_frames.py" full page/index.html out/film-silent.mp4 --workers 4
python3 "$SKILL_DIR/scripts/render_frames.py" full page/index.html out/film-4k-silent.mp4 --scale 2 --workers 4
python3 "$SKILL_DIR/scripts/render_frames.py" mux out/film-silent.mp4 out/mix.wav out/film.mp4
```

- 页面目录通过本机 HTTP 服务提供；页面引用上级目录的素材时用 `--root` 指定服务根目录。
- `--scale 2` 以 2 倍像素密度截取 CSS 1920×1080 的页面，输出 3840×2160；截图使用 DevTools 协议的缩放裁剪，与 Playwright 原生高密度截图逐像素一致。
- `full` 按 `--chunk` 秒分块，每个进程一个无头浏览器；页面崩溃或超时时重新打开并重试同一帧。分块目录名包含服务目录文件、渲染器、尺寸和缩放的指纹，内容不变时重新运行只渲染缺少的分块，`--fresh` 清空后重新开始。
- 编码：1080p 为 `libx264 -preset slow -crf 16`，4K 为 `-preset medium -crf 15 -level 5.1`，均为 `yuv420p` 与 BT.709 标记。
- `check` 退出码 1 表示跳转渲染与连续渲染结果不一致；`subtitles` 退出码 1 表示字幕文字不符、溢出或超出安全区。
- macOS 上使用 ANGLE Metal 后端，WebGL 由 GPU 渲染。

## watermark.py

```sh
python3 "$SKILL_DIR/scripts/watermark.py" video in.mp4 out.mp4
python3 "$SKILL_DIR/scripts/watermark.py" image cover.png cover-wm.jpg --position tr
python3 "$SKILL_DIR/scripts/watermark.py" video in.mp4 out.mp4 --text "进程使命" --font /path/to/font.ttf
```

默认标志为 `assets/watermark/` 中的进程使命标志。输出 JSON 报告选用的版本、区域亮度与水印位置。参数表见
[封面、水印与发布](../references/delivery.md)。

## compose_music.py

```sh
python3 "$SKILL_DIR/scripts/compose_music.py" plan.json out/music.wav --cues cues.json
```

生成 `out/music.sco` 与 32 位浮点 WAV（48 kHz 立体声，含混响尾音）。场景起点不在小节线上时打印提示。
计划格式见 [配乐、音效与旁白](../references/audio.md)。

## master_audio.py

```sh
python3 "$SKILL_DIR/scripts/master_audio.py" out/music.wav out/mix.wav --plan plan.json
python3 "$SKILL_DIR/scripts/master_audio.py" out/music.wav out/mix.wav --plan plan.json --voice voice.wav --sfx sfx.wav --target -14
```

输出 24 位 WAV 与 JSON 报告（整体与分段响度、真峰值、限制器深度）。限制器从 1 dB 开始逐级加深，直到响度达标后的真峰值不高于 `--ceiling`。

## analyze_audio.py

```sh
python3 "$SKILL_DIR/scripts/analyze_audio.py" out/mix.wav --plan plan.json --spectrum out/spectrum.png --wave out/wave.png
python3 "$SKILL_DIR/scripts/analyze_audio.py" out/mix.wav --every 20
```

## qa_frames.py

```sh
python3 "$SKILL_DIR/scripts/qa_frames.py" out/film.mp4 --cues cues.json
```

退出码 1 表示发现单帧闪烁、整帧亮度跳变或长黑场。闪烁判定要求该帧与前后两帧同向偏离，且前后两帧彼此接近；运动物体因此不会被误报。

## av_sync.py

```sh
python3 "$SKILL_DIR/scripts/av_sync.py" out/film.mp4 5.5 7.0
```

## tempo_grid.py

```sh
python3 "$SKILL_DIR/scripts/tempo_grid.py" --timeline timeline.json --major title,bridge,close
python3 "$SKILL_DIR/scripts/tempo_grid.py" --timeline timeline.json --major title,bridge,close --bpm 120
```

第一条列出偏移最小的速度，第二条打印按 120 BPM 移到小节网格后的场景起点与 JSON。
