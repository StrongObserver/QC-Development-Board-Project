# RB5 Gen2 路线评审 Prompt - 公司内部 AI

我在做一个 RB5 Gen2 / QCS8550 / Android 端侧 AI 画质增强项目，目标是形成一个接近真实工业研发逻辑、能打动懂技术面试官的项目。

## 项目当前状态

1. 已经打通 Android CameraX ROI -> TFLite -> QNN TFLite Delegate -> HTP -> 屏幕显示的端侧超分链路。
2. 主线模型是 Real-ESRGAN general x4v3 W8A8 TFLite，已经在 Android app 里通过 QNN Delegate 跑通。
3. Real-ESRGAN app fixed sample 成功，最终 smoke 约 `pre=8ms / inf=4ms / post=47ms / total=59ms`。
4. Real-ESRGAN live ROI repeated app e2e 约 `p50/p95=63/66ms`，其中 QNN inference 约 `3/3ms`。细分 profiling 显示主瓶颈是 `ImageProxy.toBitmap()` 全帧 4000x3000 转 Bitmap，约 `p50/p95=41/43ms`。
5. 我又引入 QuickSRNetSmall W8A8 作为轻量候选模型。host full 24-case 对比中：
   - QuickSRNetSmall W8A8 模型约 `43,672 bytes`
   - Real-ESRGAN W8A8 模型约 `1,308,432 bytes`
   - QuickSRNetSmall host LiteRT p50 平均约 `8.512ms`
   - Real-ESRGAN W8A8 host LiteRT p50 平均约 `344.932ms`
   - QuickSRNetSmall 平均 PSNR 比 Real-ESRGAN 高 `+2.31dB`
6. QuickSRNetSmall W8A8 已接入 Android app fixed sample 路径，并通过 QNN Delegate / HTP 跑通：
   - QuickSRNet app fixed sample 约 `pre=7ms / inf=3ms / post=39ms / total=49ms`
   - app 输出和 host 输出同输入对齐：`PSNR=46.92dB / MAD=0.939 / max abs diff=6`
7. 在三个结构风险 case 上，QuickSRNetSmall app 输出也明显更接近 HR：
   - `low_light_div2k0852`: QuickSRNet 比 Real-ESRGAN 高 `+1.62dB PSNR`
   - `people_scene_div2k0832`: QuickSRNet 比 Real-ESRGAN 高 `+3.60dB PSNR`
   - `text_signage_urban076`: QuickSRNet 比 Real-ESRGAN 高 `+1.09dB PSNR`
8. 人眼观察也显示：Real-ESRGAN 更锐、更有视觉冲击，但在树枝分叉、文字/人脸等结构场景容易糊成一团或生成错误细节；QuickSRNetSmall 更保守、更软，但结构更稳定。

## 当前路线选择难点

我不确定是否应该把项目设计成“Real-ESRGAN 主模型 + QuickSRNetSmall 候选模型，按场景选择”。

这个方案效果上有收益，但真实工业场景还要考虑：

- 模型常驻内存
- 初始化耗时
- 模型切换成本
- 功耗和温度
- 测试复杂度
- 维护复杂度
- 是否值得为了少数结构风险场景引入第二模型

## 希望你帮我判断的问题

请你站在真实手机/相机影像算法产品研发角度，帮我判断：

1. 这种主模型 + 轻量候选模型的策略，在工业上是否合理？什么情况下合理，什么情况下不合理？
2. 除了效果指标 PSNR/SSIM 和人眼 review，还应该补哪些关键数据，才能证明这个策略值得？
3. 如果要做模型选择策略，应该优先做手动场景规则、轻量场景分类器，还是暂时别做自动切换？
4. 如何权衡 Real-ESRGAN 的锐化/感知增强收益和 QuickSRNet 的结构保真/低成本收益？
5. 面试/项目展示时，怎样讲这个技术路线，才显得像真实工程判断，而不是堆模型？
6. 是否建议继续做 AIMET 精度恢复、native preprocessing/copy reduction、功耗测试，还是优先验证双模型策略的资源成本？
7. 如果你认为这条路线不合理，请指出更工业化、更可落地的替代路线。

## 请按以下格式回答

- 总体判断
- 工业场景下必须补测的数据
- 推荐路线
- 不建议做的事情
- 项目展示/简历表达建议
- 下一步最小可执行任务
