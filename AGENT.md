# CP-Agent 项目文档

## 项目概述
全自动算法竞赛出题 AI Agent 框架，从题目概念到完整数据包一键生成。

## 架构
```
cp-agent/
├── main.py              # CLI 入口
├── agent.py             # Agent loop（LLM function calling）
├── pipeline.py          # 9 个沙盒 tool 函数 + Pipeline 类
├── config.py            # YAML 配置加载器
├── config.yaml          # 所有配置（供应商、难度、算法主题）
├── testlib.h            # Codeforces 官方测试库
├── problem_db/          # 原题查重系统
│   ├── __init__.py      # CLI：crawl / enrich / import / build / search
│   ├── __main__.py      # python -m problem_db 入口
│   ├── crawler.py       # CF API 爬虫 + 限速
│   ├── cf_enrich.py     # CF 题面补爬（多线程，5 workers）
│   ├── import_deepmind.py  # 从 DeepMind code_contests 导入 CF 题面
│   ├── import_luogu.py  # 从 GitHub 导入洛谷题目
│   ├── luogu_enrich.py  # 洛谷题面爬虫（多线程）
│   ├── luogu_enrich_fast.py  # 洛谷题面快速爬虫（单线程）
│   ├── embedder.py      # 本地 embedding 模型
│   └── index.py         # FAISS 向量索引 + SQLite 元数据
├── problem_data/        # 数据文件
│   ├── problems.db      # SQLite 题库（24071 题）
│   ├── problems.faiss   # FAISS 索引（384 维）
│   └── problems.map.json
├── templates/           # C++ 模板文件
├── problems/            # 生成的题目目录
└── README.md
```

## 核心工作流（Agent 模式）
LLM 通过 function calling 自主驱动：
```
1. 构思题目 → 生成 problem.md
2. search_problem_db 本地题库查重（发现原题则换题）
3. 生成 solution / generator / validator / naive
4. 编译 → 生成数据 → 校验 → 求解 → 对拍
5. 出错则检查修复、重试
```

## 11 个 Tool

| Tool | 参数 | 沙盒 | 说明 |
|------|------|------|------|
| `read_file` | `path` | ✅ | 读文件 |
| `write_file` | `path`, `content` | ✅ | 写文件 |
| `edit_file` | `path`, `old_text`, `new_text` | ✅ | 搜索替换 |
| `list_files` | `dir` | ✅ | 列目录 |
| `compile_cpp` | `source`, `output` | ✅ | 编译 C++ |
| `generate_test_data` | `count` | ✅ | 生成 .in |
| `validate_inputs` | 无 | ✅ | 校验输入 |
| `run_solution` | `timeout_sec` | ✅ | 运行标程（超时=标程有误） |
| `stress_test` | `count` | ✅ | 对拍（naive>10s 算通过，std 超时算失败） |
| `search_problem_db` | `query`, `top_k` | — | 本地 hybrid 题库查重 |
| `web_search` | `query` | — | 搜索网页 |

## LLM 供应商（config.yaml）

| 供应商 | 协议 | 默认模型 | env_key |
|--------|------|---------|---------|
| anthropic | anthropic | claude-sonnet-4-20250514 | ANTHROPIC_API_KEY |
| openai | openai | gpt-4o | OPENAI_API_KEY |
| deepseek | openai | deepseek-chat | DEEPSEEK_API_KEY |
| ollama | openai | qwen2.5-coder:14b | 无需 |
| mimo | openai | mimo-v2.5-pro | 直接写在 env_key 里 |

API key 优先级：CLI --api-key > config yaml api_key > env_key（先查环境变量，再当 key 用）

## 难度系统
Codeforces 分数制：800-3000，步长 100，共 23 档。
- 分数只表示难度，不绑定算法或数据规模
- 算法由 `--topic` 指定，N/时间/内存由 LLM 自行决定

## 使用方式
```bash
conda activate cp-agent

# Agent 模式（默认）
python main.py --topic dp --difficulty 1800 --provider mimo --max-iterations 40

# Pipeline 模式（无 LLM，对已有题目跑流水线）
python main.py --pipeline problems/my_problem/

# 原题查重系统
python -m problem_db crawl codeforces          # 爬 CF 元数据
python -m problem_db import codeforces          # 导入 DeepMind CF 题面
python -m problem_db import luogu               # 导入洛谷题目
python -m problem_db enrich codeforces 0 5      # 补爬 CF 题面（5线程）
python -m problem_db build                      # 建 FAISS 索引
python -m problem_db search "线段树 区间GCD"     # 搜索相似题
```

## 沙盒规则
- 所有 path 必须是相对路径
- 拒绝 `..`、绝对路径
- resolve 后必须仍在 problem_dir 内

## 对拍超时策略
- `run_solution`：单个 .in 超时 → 返回 `timeout: true`（标程有误）
- `stress_test`：std 超时 5s → 失败；naive 超时 10s → 通过并提前结束

## Agent Loop
- 双协议支持：Anthropic（content blocks）和 OpenAI（tool_calls）
- 消息格式自动适配
- 最大迭代次数可配（默认 30）
- 每轮 LLM 返回 tool_use → 执行 → 返回 tool_result → 循环
- 返回 text（无 tool）→ 结束

## validator 正确写法
```cpp
#include "testlib.h"
int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    int n = inf.readInt(1, 100000, "n");
    inf.readEoln();
    // ... validate fields ...
    inf.readEof();
    return 0;
}
```
不要用 registerValidation()，必须用 registerGen + inf.init。

## 原题查重系统

### 数据来源

**Codeforces（12228 题）**
1. `crawler.py` — CF API `problemset.problems` 获取全部题目元数据（标题、标签、分数）
2. `import_deepmind.py` — 从 HuggingFace `deepmind/code_contests` 下载 parquet，提取 CF 题面（4118 题）
3. `cf_enrich.py` — 多线程补爬剩余题面（5 workers，3-8s 延迟，~50 题/分钟）
   - URL: `https://codeforces.com/contest/{cid}/problem/{index}`
   - 解析 `<div class="problem-statement">` 提取 HTML 题面
   - 结果：11985/12228（98.0%）有完整题面

**洛谷（11843 题）**
1. `import_luogu.py` — 从 GitHub `Molmin/luoguProblems-datas` 下载元数据
   - `https://raw.githubusercontent.com/Molmin/luoguProblems-datas/main/data/P.json`
   - `https://raw.githubusercontent.com/Molmin/luoguProblems-datas/main/data/SP.json`
   - 包含：难度、标签、统计（通过率、提交数）
2. 同一脚本从 `OldAntique110/Luogu-Problems` 下载题面
   - `https://raw.githubusercontent.com/OldAntique110/Luogu-Problems/main/P{pid}.md`
   - 结果：7717/11843（65.2%）有完整题面（P9000+ 未覆盖）
3. `luogu_enrich_fast.py` — 直接爬取洛谷网页补全题面
   - 从 `<script id="lentille-context">` 提取内嵌 JSON 数据
   - 包含：题目描述、输入格式、输出格式、提示
   - 结果：10789/11843（91%）有实质内容，P9000+ 100% 覆盖
   - 速率：~115 题/分钟，总耗时 ~33 分钟
   - 剩余 1024 题（8%）为 SPOJ 系列，在洛谷上无完整题面

### 技术栈
- Embedding：`paraphrase-multilingual-MiniLM-L12-v2`（384 维，本地推理）
- 索引：FAISS IndexFlatIP（余弦相似度）
- 存储：SQLite（题库）+ FAISS 文件 + JSON 映射

### 使用方法
```bash
# 爬取 CF 元数据
python -m problem_db crawl codeforces

# 导入 DeepMind CF 题面（需代理访问 HuggingFace）
export HUGGING_FACE_HUB_TOKEN="your_token"
python -m problem_db import codeforces

# 补爬 CF 题面（多线程）
python -m problem_db enrich codeforces 0 5

# 导入洛谷（从 GitHub）
python -m problem_db import luogu

# 补全洛谷题面（直接爬取洛谷网页）
python -m problem_db enrich_luogu 0 3 2.0    # 全量，3 workers，2s 延迟
python -m problem_db enrich_luogu 100 3 2.0  # 仅前 100 题

# 重建 FAISS 索引
python -m problem_db build

# 搜索相似题
python -m problem_db search "动态规划 背包"
```

## 查重流程

Agent 模式下，LLM 在构思题目后会调用 `search_problem_db` 查重：
1. 用题目关键词搜索本地 hybrid 索引（FAISS + FTS/LIKE + 术语 rerank）
2. 最高相似度 > 0.85 → 判定为重复，换题
3. 0.70-0.85 → 需人工确认或微调
4. < 0.70 → 通过

实际查重示例（2026-06-08 生成的题）：

| 生成题目 | 最相似原题 | 相似度 | 判定 |
|---------|-----------|--------|------|
| Weighted Bracket Sequence | CF 3D: Least Cost Bracket Sequence | 0.67 | ⚠️ 高度相似（需换题） |
| Range GCD Queries | CF 1111E: Tree | 0.57 | ✅ 通过 |
| Bounded Difference Subsequence | CF 661D: Maximal Difference | 0.69 | ✅ 通过 |

**经验**：括号序列+代价替换、数组求和等经典套路容易撞题，Agent 应避免。

## 已知问题
1. testlib.h 在 problem_dir 里找不到（在项目根目录），Agent 不知道
2. web_search 用 DuckDuckGo HTML 解析，质量不稳定
3. macOS 没有 bits/stdc++.h，需用标准头文件
4. ~~洛谷 P9000+ 题目无题面~~ ✅ 已通过 `luogu_enrich_fast.py` 补全（100% 覆盖）
5. AtCoder 爬虫暂未实现（API 需要认证）
6. HuggingFace 下载需要代理：`export https_proxy=http://127.0.0.1:7897`
7. CF Gym 无法爬取 — 页面有 Cloudflare 防护，API 只返回元数据不返回题面
8. 洛谷 SPOJ 系列（SP 开头）约 1024 题无题面 — 洛谷上本身就没有完整页面
