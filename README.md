# CP-Agent: 算法竞赛全自动出题框架

全自动化的算法竞赛（Competitive Programming）题目生成 Agent，从题目概念到完整数据包一键生成。

## 功能特性

- 🤖 **AI 出题**：基于 Claude API 自动生成题面、标程、生成器、校验器、暴力解
- 🔧 **自动化流水线**：编译 → 生成数据 → 校验 → 求解 → 对拍，全自动完成
- 📦 **标准数据包**：兼容 Polygon/Hydro/HustOJ 目录结构
- 🎯 **多难度支持**：Codeforces 分数制 800-3000，共 23 档难度
- 🌐 **丰富算法考点**：DP、图论、树、贪心、数据结构、数学等 20+ 算法方向
- 🔍 **原题查重**：内置 24000+ 题库（Codeforces + 洛谷），FAISS 向量检索防撞题

## 环境配置

```bash
# 创建 conda 环境
conda create -n cp-agent python=3.11 -y
conda activate cp-agent

# 安装依赖
pip install anthropic openai pyyaml requests sentence-transformers faiss-cpu

# 设置 API Key（选择一个供应商即可）
export ANTHROPIC_API_KEY="your-key-here"      # Anthropic
export OPENAI_API_KEY="your-key-here"         # OpenAI
export DEEPSEEK_API_KEY="your-key-here"       # DeepSeek
```

## 快速开始

```bash
# 生成一道动态规划题（CF 1800 分）
python main.py --topic dp --difficulty 1800

# 生成一道图论困难题，自定义名称
python main.py --topic graph --difficulty 2200 --name "shortest_path_hard"

# 使用 DeepSeek 生成题目
python main.py --topic tree --difficulty 1500 --provider deepseek

# 仅运行流水线（对已有题目目录）
python main.py --pipeline problems/my_problem/

# 查看可用算法主题
python main.py --list-topics

# 查看难度预设
python main.py --list-difficulties

# 查看可用 LLM 供应商
python main.py --list-providers
```

## 输出目录结构

```
problems/<problem_name>/
├── problem.md          # 题面（Markdown + LaTeX）
├── solution.cpp        # 标程（高效 C++ 解法）
├── generator.cpp       # 数据生成器（testlib.h）
├── validator.cpp       # 输入校验器（testlib.h）
├── naive.cpp           # 暴力解（用于对拍）
├── bin/                # 编译产物
├── inputs/             # 自动生成的 .in 文件
└── outputs/            # 标程运行生成的 .out 文件
```

## 流水线步骤

1. **编译** — 编译 generator、validator、solution、naive
2. **生成数据** — 运行 generator 生成随机 + 边界测试数据
3. **校验输入** — 运行 validator 检查所有输入是否合法
4. **生成输出** — 运行 solution 为每个输入生成输出
5. **对拍验证** — naive 与 solution 对比数万组数据，确保正确性

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | CLI 入口，参数解析 |
| `agent.py` | 核心 Agent，调用 Claude API 生成所有文件 |
| `pipeline.py` | 自动化流水线：编译、生成、校验、对拍 |
| `config.py` | 全局配置、难度预设、算法主题映射 |
| `config.yaml` | LLM 供应商、难度、算法主题配置 |
| `testlib.h` | Codeforces 官方测试库（用于 generator/validator） |
| `problem_db/` | 原题查重系统（爬虫 + 向量索引） |

## 原题查重系统

内置题库包含 **24000+ 道题目**，支持向量相似度检索：

| 来源 | 题数 | 有实质内容 | 覆盖率 |
|------|------|-----------|--------|
| Codeforces | 12,228 | 11,985 | 98% |
| 洛谷 | 11,843 | 10,789 | 91% |
| **总计** | **24,071** | **22,774** | **95%** |

### 使用方法

```bash
# 搜索相似题（查重）
python -m problem_db search "动态规划 背包"
python -m problem_db search "线段树 区间GCD"

# 重建索引（添加新题目后）
python -m problem_db build

# 导入洛谷题目
python -m problem_db import luogu

# 补全洛谷题面
python -m problem_db enrich_luogu 0 3 2.0
```

### 技术栈

- **Embedding**：`paraphrase-multilingual-MiniLM-L12-v2`（384 维，本地推理）
- **索引**：FAISS IndexFlatIP（余弦相似度）
- **存储**：SQLite（题库）+ FAISS 文件 + JSON 映射
