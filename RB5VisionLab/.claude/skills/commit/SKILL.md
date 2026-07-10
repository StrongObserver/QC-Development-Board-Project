---
name: commit
description: 本项目（RB5VisionLab）的 git 提交规范与流程。当用户要求"提交/commit/保存进度/git commit/记录这一步"时使用。规则：单人 main 主线、小步提交、提交前先 Gradle 构建验证（真机 adb 验证由用户跑）、只提交源码+必要 assets 不提交生成物。Claude 可直接执行 git add/commit；身份 StrongObserver / 858922998@qq.com。
---

# Commit 规范（RB5VisionLab）

> 单人开发、纯 `main` 主线、小步可回滚。本 skill 既是规则，也是 Claude 执行"提交"任务的标准流程。

## 0. 环境事实（已验证 2026-06-20）
- **Claude 能直接执行 git**：`git status / add / rm --cached / commit / log / diff` 在沙箱内均正常。
- **真机与 GPU 必须用户跑**：Claude 沙箱的 `/dev` 是最小集、**无 USB / 无 nvidia**，所以
  `adb install / am start / logcat / screencap` 与任何 GPU 命令 Claude 跑不了 → **Claude 只负责
  `./gradlew` 构建 + 给真机命令，由用户在自己终端执行、把结果/截图贴回**。
- **沙箱噪声**：`git status` 里可能出现 `.bashrc/.zshrc/.gitconfig/.mcp.json/.github/scripts/.vscode/.ripgreprc`
  等"未跟踪"项——那是沙箱把这些名字映射成 `/dev/null` 字符设备的假象，**不是真文件、git 不会提交**，忽略。
  只 `git add` 本步真实涉及的文件。
- **`git config` 写入可能失败**（`.git/config` 是绑定挂载点）；不要紧：身份已是
  `StrongObserver / 858922998@qq.com`，提交自动用它，无需改 config。
- **构建必须用 Android Studio 的 JBR**：命令行默认 java 版本不对，本工程 Gradle 需要它自带的 JDK。

## 1. 硬规则
1. **单人 + 单 `main`**：只在 main 上推进；不开分支/不合并，除非用户明确要求。
2. **一步一提交**：每个 commit 只含**一个已验证的小步骤**；不把多个无关改动塞进一个 commit。
3. **提交前先验证**：
   - 改了 app 代码（Kotlin/C++/Gradle/资源）→
     `JAVA_HOME=/opt/android-studio/jbr ./gradlew --no-daemon :app:assembleDebug` 必须 **BUILD SUCCESSFUL**。
   - 需**真机**验证（行为/显示）而本次未在真机验证 → 可提交，但**必须在 commit body 注明
     "未真机验证 + 待验证项"**，不许谎报。
4. **只提交源码 + 必要 assets，不提交生成物/大文件**：
   - 提交：`*.kt`、`*.cpp`、`CMakeLists.txt`、`*.gradle.kts`、`libs.versions.toml`、布局/manifest、
     以及 app 运行必需的 `app/src/main/assets/*.tflite`、测试图。
   - **不提交**：`.gradle/`、`app/build/`、`app/.cxx/`、`.idea/workspace.xml`、`*.apk`、`local.properties`、
     构建日志/截图（如 `b3_build.log`、`sr_screen.png`）。
   - **PC 实验区 `RB5_SR_lab/` 在本仓库之外**，不纳入本仓库。
5. **显式审查再暂存**：先 `git status` + `git diff --stat` 看清，确认都属"同一个小步骤"、无生成物/噪声混入，
   再 `git add <具体文件>`（避免 `git add -A` 误纳沙箱噪声）。
6. **不 push、不加远程、不签名**，除非用户明确要求。

## 2. commit message 格式（本项目沿用 `area: short result`）
- 首行：`area: short result` —— `area` 是模块小写前缀，`result` 一句话祈使，≤ ~50 字。
  常用 area：`app`(Kotlin/UI)、`native`(C++/JNI)、`camera`、`gradle`、`docs`。
  - 例：`app: on-device TFLite super-resolution on static image (B3)`、`docs: record A2 export`。
- 需要时空一行写 body：说明 **改了什么 / 为什么 / 如何验证**（与 AGENTS.md、Nutstore
  `RB5 Gen2_AI上下文.md` 的 what-why-how 一致）。若该步由 **GPT-5.5/Codex** 协作实现或审查，一并注明。
- body 末尾署名：
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```

## 3. Claude 执行"提交"的标准流程
1. **构建门禁**：跑 `JAVA_HOME=/opt/android-studio/jbr ./gradlew --no-daemon :app:assembleDebug`，
   结果如实写进 message（通过 / 未真机验证）。
2. **审查改动**：`git status` + `git diff --stat`，确认同一小步、无生成物/大文件/沙箱噪声混入。
3. **暂存**：`git add <本步涉及的具体文件>`。
4. **提交**（Claude 直接执行，本地可回滚）：
   ```bash
   git commit -m "area: short result" -m "<改了什么/为什么/如何验证>" \
     -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
   ```
5. **回报**：贴出 `git log --oneline -1` 与本次涉及文件；提醒把进展同步到 `AGENTS.md`
   与 Nutstore `RB5 Gen2_AI上下文.md`（Milestone / 下一步）。
6. 改动较大或有正确性风险时，**先按 `CLAUDE.md` 调 Codex(GPT-5.5) review（务必先对齐上下文：
   背景/已试过什么/现象/文件绝对路径/契约约束），再提交**。

## 4. 已确认配置（无需再问）
- git 身份：`StrongObserver / 858922998@qq.com`（已生效）。
- 远程仓库：**无**；不 push。commit 签名（GPG/`--signoff`）：**不需要**。
- 回滚：`git reset --soft HEAD~1`（保留改动）或 `git reset --hard HEAD~1`（丢弃，谨慎，需先告知用户）。
