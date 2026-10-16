# 主页维护

## 内容在哪里修改

- `README.md`：个人主页默认显示的中文版。
- `README.en.md`：英文版，新增项目时同步修改。
- `assets/hero-light.svg`、`assets/hero-dark.svg`：定制封面，跟随阅读环境切换配色。
- `docs/casebook.md`：AI 网关、LLM 训练推理与 Agent RL 的公开案例入口。
- `scripts/update_activity.py`：贡献图表生成脚本，仅依赖 Python 标准库。
- `.github/workflows/update-profile.yml`：GitHub Actions 每日更新配置。

仓库根目录的 `README.md` 会直接显示在 [GitHub 个人主页](https://github.com/Lingbo-Huang)。

## 自动图表

每天北京时间 **09:17** 计划运行一次，也可以在仓库 Actions 页面打开 **Update profile activity**，点击 **Run workflow** 手动刷新。GitHub 定时任务可能延迟，图中会保留最近一次成功更新日期。

图表以 GitHub GraphQL 为数据来源，包含最近 **13 个完整的 7 天窗口**，以及最近 **90 个完整 UTC 日**的汇总。当天尚未结束的数据不会纳入统计。周趋势使用公开主页展示的贡献计数，可能包含用户选择公开的匿名私有贡献；不展示私有仓库名称或内容。提交、PR、Issue 的分类数字只计算公开仓库贡献。

“贡献次数”遵循 GitHub 的贡献统计口径，不等同于原始 Git 提交数量；PR、Issue 分类指创建的条目。图表用于展示持续工程活动，不用于表示语言熟练度。统计来源与更新时间也写在 SVG 图中。

浅色、深色及手机图表都保存在本仓库，不依赖第三方统计卡片服务。API 请求失败时，工作流报错并保留上一版图表。

## 权限与运行

工作流仅使用仓库自带的 `GITHUB_TOKEN`，不需要额外创建或保存个人访问令牌。写权限仅用于把更新后的 SVG 提交回这个主页仓库；脚本不写入或输出令牌，也不保存完整 API 响应。

工作流在默认分支运行，支持手动触发、每日定时触发，以及脚本或工作流修改后的自动触发。图表更新提交不会再次触发生成，避免循环。

## 添加一个更有说服力的案例

每个案例建议包含：

1. 具体问题与约束：为什么做、已有方案的缺点是什么。
2. 架构与关键决策：一张图解释请求或训练数据如何流转。
3. 可运行的核心代码与复现说明。
4. 验证方法：性能、正确性或任务成功率，以及测试环境。
5. 对照结果与限制：用真实数据解释改进了什么。

涉及非公开工作的材料，先整理成可公开的设计说明或独立示例，再补充主页链接。能力名称可以先保留，项目结果、吞吐量和训练指标应在实际测量后填写。

## 官方参考

- [GitHub 个人主页 README](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
- [GitHub Actions 定时任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GITHUB_TOKEN](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication)
- [GitHub GraphQL 用户与贡献数据](https://docs.github.com/en/graphql/reference/objects#contributionscollection)
