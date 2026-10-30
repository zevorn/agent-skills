---
# SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
# SPDX-License-Identifier: MIT
name: promo-video
description: >-
  Produce frame-exact promotional, comparison, and explainer videos from code and real data: a fact-checked
  storyboard, a deterministic HTML compositor rendered frame by frame with headless Chromium, 1080p or 4K output,
  an original score and cue-driven sound effects on a shared bar grid, loudness mastering, picture and audio QA,
  covers, publishing copy, and a Process Mission watermark by default. Use for product films, OS or simulator
  comparisons, platform showcases, and Bilibili or YouTube uploads.
---

# 代码渲染宣传片

画面由代码逐帧算出，每一帧都是时间的纯函数；画面、数据、配乐与音效共用一份时间轴；片中的命令、输出和数字全部来自可以复现的记录。
成片与封面默认加进程使命（Process Mission）水印。

## 成片标准

- **真实**：每个数字在事实核对表中有出处；对比双方的配置差异写进画面脚注；测量范围写进文案文档。无法核实的产品说法交给用户确认后再使用。
- **确定**：任意帧可以单独渲染，随机顺序与连续顺序渲染的结果一致，中断后可以接着渲染。
- **同一时间轴**：场景起点、画面事件、配乐小节与音效提示点从同一个文件读取。修改时间只改这个文件。
- **可读**：每一刻只有一个视觉焦点；字幕一次一句完整的话；文字不重叠、不出画，停留时间足够读完。
- **声音**：原创配乐与程序合成音效；无旁白的成片约 −15 LUFS，有旁白约 −14 LUFS，真峰值不高于 −1 dBTP。
- **可重建**：交付时附带分镜、数据来源、测量范围与重新生成命令。

## 工作流程

1. **收集事实与素材**：找到实验记录、日志、仓库文件和已有渲染结果；列出每个候选数字的来源、条件和负载。产品能力的描述（例如“统一开发体验”）单独列出，交给用户核实。
2. **叙事与分镜**：按“开场钩子 → 主张 → 方法或平台 → 逐项实测 → 收尾”组织，让后面的实测逐条回应前面的主张。写分镜表、事实核对表与字幕。见 [叙事、分镜与事实核对](references/storyboard.md)。
3. **时间轴**：选定速度（120 BPM 时一小节 2 秒），用 `scripts/tempo_grid.py` 把场景起点放到小节线或半小节上；画面内事件的偏移量写进同一个时间轴文件。
4. **画面素材**：机器人、物理场景、芯片等三维画面用实际记录离线渲染成图片序列（目标分辨率的 2 倍超采样）；网页界面、终端与控制面板按视频风格重新绘制，数值逐帧回放记录。需要 4K 时素材按 2 倍尺寸渲染。
5. **合成页面**：从 `assets/page-template/` 开始，实现 `window.ready`、`window.FPS`、`window.DURATION` 与 `window.renderFrame(frame)`，提示点通过 `window.getCues()` 导出，字幕通过 `window.getSubtitles()` 导出。见 [合成页面约定](references/page-contract.md)。
6. **预览与画面质检**：每个转场前后与每段中间截帧拼成联系表；运行 `qaText` 检查文字几何；`render_frames.py check` 对比直接跳转与连续推进的渲染结果，`subtitles` 检查字幕位置并导出 SRT。见 [质检](references/qa.md)。
7. **配乐、音效与旁白**：写音乐计划，`scripts/compose_music.py` 生成配乐并合入页面提示点；`scripts/master_audio.py` 做电平推子、旁白闪避与母带；`scripts/analyze_audio.py` 检查分段响度与频段分布。见 [配乐、音效与旁白](references/audio.md)。
8. **渲染与合成**：`scripts/render_frames.py full` 分块并行渲染（`--scale 2` 输出 3840×2160），`mux` 合入音轨；`scripts/qa_frames.py` 扫描单帧闪烁与长黑场，`scripts/av_sync.py` 测量重击处音画偏移。
9. **水印**：`scripts/watermark.py video` 与 `scripts/watermark.py image` 给成片和封面加水印，默认使用进程使命标志，按所在角落的亮度自动选择浅色或深色版本。
10. **封面与发布文案**：用实测同一时刻的真实画面制作 16:9 与 4:3 封面，在缩略图尺寸检查可读性；写标题、简介、章节与标签。见 [封面、水印与发布](references/delivery.md)。
11. **交付**：成片（按需 1080p 与 4K）、音乐文件、封面、文案文档（分镜与旁白、音乐结构、数据来源、测量范围、重新生成命令）。

## 规则

- 画面中的每个数字、命令和输出都能追溯到记录；记录里没有的量不画进画面。只有部分条件成立的结果，在同一画面写明条件。
- 对比双方的版本、配置或算法有差异时（例如一方启用了额外控制器或优化参数），在该段脚注中写明；结论只覆盖测量过的范围。
- 演示的系统与实际产品形态有区别时（例如只运行了产品的一部分），在文案文档的测量范围中写明，画面用词与实际运行内容一致。
- 用户提供的产品描述保持原意；扩写出的具体能力在交付说明中列出，请用户核实。
- 网页或终端画面按视频风格重绘时，保留原界面的结构与配色关系，数值来自运行记录；记录缺少的字段不显示。
- 转场时上一段的标题先淡出，下一段标题再进入，避免同位置标题叠化。
- 修改时间后重新生成配乐，并在新画面上复查每个音画同步点。
- 不在交付内容中保留修改过程；文案只描述成片的最终状态。

## 脚本

| 脚本 | 作用 |
| --- | --- |
| `render_frames.py` | 截帧与联系表（`snap`）、分块并行渲染并在中断后继续渲染（`full`）、执行页面质检表达式（`eval`）、确定性对比（`check`）、字幕检查与 SRT 导出（`subtitles`）、合入音轨（`mux`） |
| `watermark.py` | 视频与图片水印；默认进程使命标志，可换标志、文字、位置、大小、透明度与显示时段 |
| `compose_music.py` | 读取音乐计划与页面提示点，生成 Csound 乐谱并渲染配乐 |
| `master_audio.py` | 分段电平、旁白闪避、音效混合、均衡与压缩、响度标准化、真峰值限制 |
| `analyze_audio.py` | 分段响度与六个频段的能量占比，输出频谱图与波形图 |
| `qa_frames.py` | 成片单帧闪烁、整帧亮度跳变与长黑场扫描 |
| `av_sync.py` | 指定时间窗内画面亮度跳变与声音起音的偏移 |
| `tempo_grid.py` | 为场景起点寻找合适速度，或按给定速度把场景起点移到小节线与半小节上 |

依赖、参数与退出码见 [scripts/README.md](scripts/README.md)。
