# EvalHub Manual Download Queue

更新时间：2026-07-17

这些源当前不由 AI 自动下载。原因通常是超过 3GB、需要登录/表单/网盘、或需要遵守数据集申请条款。下载后放到指定路径，再运行对应准备脚本或补 manifest。

## RealSR

用途：真实相机退化 SR。用于项目进入“真实相机退化鲁棒性”声明前，弥补当前 DIV2K/Urban100/Set14 都是合成退化的缺口。

状态：已手动下载并放入 `evalhub_data\raw\realsr`，已派生 `RealSR V3 x4 Test` EvalHub 层。

官方仓库：

```text
https://github.com/csjcai/RealSR
```

README 中 Version 3 链接：

```text
Google Drive:
https://drive.google.com/open?id=17ZMjo-zwFouxnm_aFM6CUHBwgRrLZqIM

Baidu Drive:
https://pan.baidu.com/s/1dn4q-7E2_iJkNXx4MPdVng
code: 2n93
```

目标路径：

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\raw\realsr
```

当前派生结果：

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\derived\realsr_v3_x4_test_128x4_v1\manifest.csv
cases: 100
```

要求：

- 下载真实数据包，不要只下载 `RealSR-master.zip` 源码仓库。
- 优先 Version 3，因为 HR/LR 分辨率不同，更接近真实 SR。
- 如果下载包很大，保留原始压缩包和解压目录，并记录文件名。

## TextZoom

用途：文字/标识保真 SR。用于 `text_signage` 类别失败、文字可读性专项、或 app demo 需要证明文字不被模型扭曲时。

状态：已手动下载并放入 `evalhub_data\raw\textzoom`，已派生 TextZoom test easy/medium/hard EvalHub 层。

官方/常见入口：

```text
https://github.com/WenjiaWang0312/TextZoom
```

目标路径：

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\raw\textzoom
```

当前派生结果：

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\derived\textzoom_test_128x4_v1\manifest.csv
easy: 1619
medium: 1411
hard: 1343
total: 4373
```

要求：

- TextZoom 常见格式是 LMDB，例如 `data.mdb` / `lock.mdb`。
- 下载后不要尝试用普通图片浏览器直接打开 LMDB。
- 后续需要单独写 extractor/manifest，把 easy/medium/hard 或 train/test 子集映射到 EvalHub。

## Manga109

用途：漫画/线稿/高对比边缘/文字框类压力测试。当前不是 RB5 项目主线 P1，不建议阻塞。

状态：不作为当前必需下载项；用户已申请，等待通过即可。当前评测体系已有 Set14/Urban100/TextZoom 覆盖大部分结构/文字风险。

官方入口：

```text
https://manga109.github.io/manga109-project-website/en/download.html
```

目标路径：

```text
C:\Users\Admin\Desktop\QC-Development-Board-Project\evalhub_data\raw\manga109
```

要求：

- 遵守官方申请和使用条款。
- 当前项目已经有 Urban100/Set14/TextZoom 方向可覆盖大部分结构/文字风险，Manga109 只作为后续可选扩展。

## 手动下载后如何接入

1. 把原始压缩包和解压目录放到对应 `evalhub_data\raw\<dataset_id>\`。
2. 不要提交 `evalhub_data\`。
3. 运行：

```bat
python -B eval_hub\scripts\evalhub_status.py
```

4. 如果状态仍然是 missing，说明还需要为该数据源写 prepare 脚本或更新 `dataset_is_present` 判定。

