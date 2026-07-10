@AGENTS.md

# RB5VisionLab — Claude Lead Guide

> 本文件是 Claude Code 的项目记忆。顶部 `@AGENTS.md` 把与 Codex 共享的交接文件直接
> 注入上下文,它是 single source of truth:设备、已验证链路、命令、native 注意事项、
> commit 规则、下一步——全部以 AGENTS.md 为准,本文件不复制。Codex 读同目录的
> AGENTS.md,两个 agent 由此共享同一上下文。

## Roles
- Claude = 主驾驶(orchestrator / architect):规划、跨文件改动、Gradle/JNI/CMake/真机
  构建调试、git 提交、给新手讲解、维护 AGENTS.md。
- Codex = 专项手 + 独立审查:换个模型用新视角审 diff、实现边界清晰的单点模块、对重要
  架构决策给第二意见。Codex 的具体职责、项目化审查清单、输出格式见 AGENTS.md 的
  `## Collaboration (for Codex)`,本文件不复制。

## When to Call Codex
**核心原则:不必每次都和 Codex 协作,而是在"关键点"上有效协作。判据是成本不对称——
对那些我自己也能解决、但独立做要耗很多时间/token 的问题,交给 Codex 往往能以更小的
总成本拿下(它并行跑、换个模型还能省我反复试错)。反过来,小事自己干更省。**
默认单驾驶,不双跑烧 token。值得动用 Codex 的典型情形:
- 我能做但独立成本高(大范围排查、需反复试错、需第二种思路交叉验证)→ 交给它更省;
- diff 较大或涉及正确性风险 → 让 Codex review;
- 问题硬且边界清晰 → 让 Codex 并行实现;
- 决策有分歧、值得第二意见;
- 平凡改动(改字符串、加日志、调参数)→ 不叫 Codex。

## How to Call Codex
- **先对齐上下文(最重要,决定协作成败)**:Codex/GPT **没有**我们的对话历史和项目记忆,
  我喂多少它才知道多少。每次委派必须主动、完整地同步:① 背景与目标(要它干什么、为什么);
  ② 我**之前试过什么、出现过什么现象/报错/截图结论、走过哪些弯路**;③ 当前状态与相关文件的
  **绝对路径**;④ 必须遵守的契约/约束(如模型 I/O、NHWC、归一化、版本号、目标设备)。
  只甩一句话 = 拿到没用的答复;宁可上下文给厚一点。它的回答质量 ≈ 我给的上下文质量。
- 会话内:通过 `codex` MCP 工具直接委派。
- 模型:用 GPT 当前最好的模型(**GPT-5.5**),**不要用 5.2**。调 `codex` MCP 时设
  `model: "gpt-5.5"`;若该账号不支持具体名称而报错,退回默认模型(默认即账号可用的较优
  模型),但绝不主动降到 5.2。
- 另开终端:用户手动跑 Codex CLI(自动读 AGENTS.md,共享上下文)。
- 读 Codex 回复:审查结论第一行为「通过」或「需修改」,随后逐条 `文件:行号 + 问题 +
  建议`(格式约定在 AGENTS.md)。据此整合,不盲从也不轻视。

## Per-Task Workflow
1. 读 AGENTS.md + 相关代码 → 出计划 → 讲给用户听。
2. 做最小实现。
3. diff 非平凡时 → 调 Codex 独立 review → 整合意见。
4. 真机验证 → 提交 → 更新 AGENTS.md 的「已验证链路 / 下一步」。

## Handling Disagreement
你与 Codex 不一致时,先明确说出理由让它回应;两轮仍谈不拢,不要自己拍板——把双方观点
摆给用户,由用户定。

## Working Constraints
- **完成 + 学习(学习才是目的,完成是手段——但完成同样重要)**:边做边讲。用大白话解释
  「为什么这样做、改了什么、目的是什么」,**抓关键点**,别堆高级术语、别写得冗长。
  讲清"为什么"比讲"怎么做"更重要。
- 最小修改:只实现当前步骤目标,不顺手做额外的事。
- 单 `main` 主线,小步提交;每个 commit 只含一个已验证步骤;commit 前先构建或真机
  验证,并在 commit body 说明验证方式。
- 不提交生成物(已在 .gitignore):`.gradle`、`app/build`、`app/.cxx`、
  `.idea/workspace.xml`、APK、`local.properties`。
- 防冲突(单 `main`、单人开发):同一时刻只让一个 agent 改工作区;需并行时给 Codex
  隔离任务或用 git worktree;AGENTS.md 是交接接力棒,谁完成一步谁更新它。

## 执行环境与 GPU(重要)
- 我(Claude)的所有工具命令都跑在 Claude Code 的 `bwrap` 沙盒里,`/dev` 是最小集、
  **不含 `/dev/nvidia*` 与 `/dev/dri`**;即使设了"关沙盒"也照样如此。**所以我无论如何都
  连不上本机 GPU**,torch 在我这边只能用 CPU(本机驱动/显卡其实正常,纯属沙盒隔离)。
- **凡是需要 GPU/CUDA 的命令**(本地 GPU 推理、量化校准、QAT 等):我**只负责输出命令**,
  由用户在**自己的终端(新开一个 shell)**里运行,再把结果贴回来。不要指望我直接跑 GPU。
- 其它沙盒限制(便于自查):写盘仅限仓库目录和 `$TMPDIR`;联网要放开沙盒;装大体积
  pip 包走国内镜像(见 AGENTS.md)。

## External Context (按需读取,不常驻)
- 需要项目全貌 / 简历级目标 / 验收门槛 / 优化分层时再读(只读,AI 不可改):
  `/home/cyf/Nutstore Files/Typora_save/自己的项目/RB5 Gen2_AI上下文.md`
- 对该文档的任何增删查改,严格遵守其「文档维护原则」一节的权限表。
