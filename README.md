# 商业地产中介 AI 智能系统

本仓库提供一个面向商业地产中介团队的轻量级 AI 决策原型，当前以酒店转让/租赁项目为示例垂类。系统不依赖第三方库，可直接读取脱敏项目和客户需求 CSV，输出客户推荐、项目洞察、风险尽调提示和经纪人任务队列。

## 核心能力

- **客户-项目智能匹配**：按城市、区域、商圈、房间数、单房租金、转让费、估算接手成本、押付压力和经营状态评分。
- **交易风险识别**：自动提示租期不足、证照/消防/特行不明、业主书面同意缺失、佣金条款未锁定等阻碍。
- **项目经营洞察**：对每个房源生成市场化评分、热推/可推/培育标签、核心卖点和下一步动作。
- **经纪人任务队列**：把推荐结果转成客户经理、交易顾问、尽调专员可执行的 CRM 任务。
- **集成友好输出**：支持文本看板和 JSON 输出，便于后续接入 CRM、BI 或大模型工作流。

## 快速开始

```bash
python3 scripts/test_env.py
python3 scripts/analyze_projects.py
python3 scripts/match_customers.py
python3 scripts/commercial_estate_ai_system.py --top-n 3
```

只查看某个客户：

```bash
python3 scripts/commercial_estate_ai_system.py --customer-id C001 --top-n 2
```

输出 JSON 供系统集成：

```bash
python3 scripts/commercial_estate_ai_system.py --json
```

## 数据文件

- `data_sample/hotel_projects_sample.csv`：脱敏商业地产项目库存。
- `data_sample/customer_requirements_sample.csv`：脱敏客户需求和风险偏好。

## 推荐业务流程

1. **早会库存盘点**：运行 `scripts/analyze_projects.py` 查看库存结构和共性风险。
2. **客户分层推荐**：运行 `scripts/match_customers.py` 或 AI 控制台筛选 A/B 级机会。
3. **尽调前置**：先处理系统提示的证照、消防、特行、业主同意和佣金条款阻碍。
4. **带看和谈判**：对高匹配且阻碍较少的项目安排现场踏勘，并复核租约原件、经营流水、租金递增和改造预算。
5. **系统集成**：使用 `--json` 输出把推荐、任务和项目洞察写入 CRM。

## 后续可扩展方向

- 接入真实 CRM 的客户跟进、带看记录和成交反馈。
- 引入 LLM 生成项目推荐话术、业主沟通纪要和尽调清单。
- 增加写字楼、商铺、产业园等更多商业地产垂类字段。
- 基于成交数据训练权重，使评分从规则引擎升级为可校准模型。
