<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission -->
<!-- SPDX-License-Identifier: MIT -->

# 质检

每一项检查都在命令行运行并记录结果；发现问题后修正页面或素材，重新渲染受影响的片段，再检查一次。

## 画面

| 检查 | 方法 | 通过条件 |
| --- | --- | --- |
| 版式 | `render_frames.py snap page.html <每段中间与转场前后的时刻>` 生成联系表 | 标题、条件标签、数字、脚注互不遮挡；转场无空白停顿 |
| 文字几何 | `render_frames.py eval page.html "window.qaText(0, window.DURATION, 0.2)"` | 重叠只出现在叠化期间；无出画、无停留过短的文字 |
| 字幕 | `render_frames.py subtitles page.html film.srt` 在每句字幕中点截帧检查包围盒并导出 SRT | 退出码 0；全部字幕在底部安全区内且无溢出 |
| 确定性 | `render_frames.py check page.html <若干时刻>` 比较直接跳转与从前一秒逐帧推进的渲染结果 | 平均像素差不超过 0.5 |
| 4K | 从 4K 成片截取 1:1 局部，与页面直接截图比较 | 文字边缘锐利，平均差约 1/255 |
| 单帧闪烁与黑场 | `qa_frames.py film.mp4 --cues cues.json` | 退出码 0；设计中的重击单独列出 |

`qa_frames.py` 的块分数参考：逐帧变化的数字约 16–18，终端整屏滚动约 24，真实闪白在 200 以上；默认阈值 30。

## 音画同步

- 列出所有同步点：场景起点、重击、状态切换、提示音。画面时刻与配乐时刻都从时间轴文件计算，逐项打印对照表。
- 在每个同步点截帧，确认画面事件确实发生在该帧（例如推力箭头出现、状态框切换）。
- `av_sync.py film.mp4 <开始> <结束>` 测量画面亮度跳变与声音起音的偏移；时间窗内应只有一个硬切或闪白，叠化与文字动画不适合用来测量。偏移在 ±70 ms 以内可以接受。

## 声音

- `master_audio.py` 报告整体与分段响度、真峰值和限制器深度；限制器深度超过 6 dB 时检查重击是否过响。
- `analyze_audio.py` 对比频段占比与参考值，并生成频谱图、波形图。
- 成片合成后复核响度与真峰值，确认音轨与视频时长相同。

## 数据

- 画面中的每个数字从原始记录重新计算一次，与汇总文件对照；取整方式全片一致。
- 回放数据的画面（曲线、计数器）抽查起点、终点与峰值三处，与记录逐值比较。
- 片中出现的配置条件与记录中的配置文件一致。

## 交付文件

```sh
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration -of compact film.mp4
```

视频与音频时长相同；H.264 High、`yuv420p`、`+faststart`；4K 为 3840×2160、Level 5.1。
