# 📖 Persona Friction Engine — User Manual (用戶手冊)

Welcome to the **Persona Friction Engine**! This manual provides complete guidance on how to run, configure, and extend the engine. It is written in both **English** and **繁體中文** to support developers, product managers, and UX researchers.

歡迎使用 **Persona Friction Engine**！本手冊提供關於如何運行、配置和擴充引擎的完整指南。我們同時提供**英文**與**繁體中文**版本，以支援開發人員、產品經理和 UX 研究員。

---

## 🗺️ Table of Contents (目錄)

1. [System Overview (系統概述)](#-system-overview-系統概述)
2. [Quick Start (快速入門)](#-quick-start-快速入門)
3. [Scenario Configuration (場景配置)](#-scenario-configuration-場景配置)
4. [Interpreting the Report (解讀審計報告)](#-interpreting-the-report-解讀審計報告)
5. [Developer Guide (開發人員指南)](#-developer-guide-開發人員指南)

---

## 1. 🗺️ System Overview (系統概述)

The **Persona Friction Engine** simulates real user behavior using demographic and cognitive profiles (Personas). It drives a headless browser, captures page screenshots, and calculates a deterministic **Cognitive Load Score (CLS)** to identify UX friction points.

**Persona Friction Engine** 透過人口統計學和認知特徵（用戶畫像 Persona）來模擬真實用戶行為。它驅動無頭瀏覽器、擷取頁面截圖，並計算出確定性的**認知負荷分數 (Cognitive Load Score, CLS)**，從而精確識別 UX 摩擦點。

### 📊 Cognitive Load Score (CLS) Formula (CLS 評分公式)

The engine calculates CLS using a three-dimensional weighted formula:

引擎使用三維加權公式計算 CLS：

$$\text{CLS} = 0.35 \times \text{VisualComplexity} + 0.40 \times \text{InteractionFriction} + 0.25 \times (100 - \text{CognitiveAlignment})$$

| Metric (指標) | Description (英文描述) | 中文說明 |
| :--- | :--- | :--- |
| **Visual Complexity** | Density of elements, text blocks, and layout clutter. | 頁面元素密度、文字區塊大小及版面雜亂度。 |
| **Interaction Friction** | Missing aria-labels, lack of visible CTAs, and broken forms. | 缺少無障礙標籤、缺乏明顯 CTA、表單設計不佳。 |
| **Cognitive Alignment** | Match between persona's tech-savviness and page complexity. | 用戶畫像的技術熟練度與頁面複雜度之間的契合度。 |

---

## 2. 🚀 Quick Start (快速入門)

### 📋 Prerequisites (先決條件)

Ensure you have Python 3.11+ and Playwright installed.

請確保已安裝 Python 3.11+ 和 Playwright。

```bash
# Clone the repository (複製倉庫)
git clone https://github.com/erickh826/persona-friction-engine.git
cd persona-friction-engine

# Install dependencies (安裝依賴)
pip install -r requirements.txt
playwright install chromium
```

### 🏃 Running a Simulation (運行模擬)

To run a simulation using a predefined scenario file:

使用預設的場景檔案運行模擬：

```bash
# Run with default settings (使用預設設定運行)
python src/main.py --scenario tests/fixtures/sample_scenario.json

# Run with LLM-based evaluation enabled (啟用 LLM 視覺評估)
export OPENAI_API_KEY="your-api-key"
python src/main.py --scenario tests/fixtures/sample_scenario.json --use-llm

# Run in visible browser mode for debugging (在可見瀏覽器模式下運行以進行偵錯)
python src/main.py --scenario tests/fixtures/sample_scenario.json --no-headless
```

---

## 3. 📝 Scenario Configuration (場景配置)

Scenarios are configured using simple JSON files. Below is an annotated example of a scenario configuration.

場景是透過簡單的 JSON 檔案配置的。以下是一個帶有註解的場景配置範例。

```json
{
  "scenario_id": "checkout-flow-busy-mom",
  "target_url": "https://shopee.tw/checkout",
  "target_goal": "Complete the purchase checkout flow under 5 steps",
  "max_steps": 5,
  "persona": {
    "name": "Amy",
    "age": 38,
    "tech_savviness": 2,
    "attention_span_seconds": 45,
    "motivation_level": 3,
    "cognitive_biases": ["loss aversion", "status quo bias"]
  }
}
```

### 🔑 Key Parameters (關鍵參數說明)

| Parameter (參數) | Type (類型) | Description (英文說明) | 中文說明 |
| :--- | :--- | :--- | :--- |
| `target_url` | String | The initial entry point URL for the simulation. | 模擬的初始入口網址。 |
| `max_steps` | Integer | Maximum interaction steps before stopping. | 停止前的最大互動步數。 |
| `tech_savviness` | Integer (1-5) | Persona's technical comfort level (1 = lowest). | 用戶的技術熟練度（1 為最低）。 |
| `motivation_level` | Integer (1-5) | Determines patience before dropping out. | 決定用戶流失（放棄）前的耐性。 |

---

## 4. 📊 Interpreting the Report (解讀審計報告)

Every run generates an interactive HTML report saved to the `output/` directory (e.g., `output/checkout-flow-busy-mom_report.html`).

每次運行都會在 `output/` 目錄中生成一個互動式 HTML 報告（例如 `output/checkout-flow-busy-mom_report.html`）。

### 📈 Report Sections (報告版塊)

1. **Audit Summary Dashboard (審計摘要儀表板)**: Shows overall Scenario ID, Persona Name, Final CLS, and total steps taken.
2. **CLS Progression Chart (CLS 趨勢圖)**: An interactive line chart displaying the composite CLS score and its three sub-metrics over time.
3. **Step Timeline (步驟時間線)**: Displays screenshots taken at each step, overlaid with red bounding boxes indicating exactly where friction points were detected.
4. **Friction Points Inspector (摩擦點檢查器)**: A detailed, color-coded table categorized by severity (Critical, High, Medium, Low) with clear recommendations.

1. **審計摘要儀表板**: 顯示整體場景 ID、用戶畫像名稱、最終 CLS 分數以及執行的總步數。
2. **CLS 趨勢圖**: 一個互動式折線圖，展示複合 CLS 分數及其三個子指標隨時間的變化趨勢。
3. **步驟時間線**: 顯示在每一步截取的畫面，並疊加紅色邊框，精確標示偵測到摩擦點的位置。
4. **摩擦點檢查器**: 一個詳細的、按顏色區分嚴重程度（關鍵、高、中、低）的表格，並提供清晰的改進建議。

---

## 5. 🛠️ Developer Guide (開發人員指南)

### 🧪 Running Tests (運行測試)

The repository comes with a comprehensive test suite (42 unit and integration tests).

本倉庫附帶完整的測試套件（包含 42 個單元測試與整合測試）。

```bash
# Run all tests (運行所有測試)
pytest -v

# Run with stdout printing (運行並列印標準輸出)
pytest -s
```

### 🧱 Project Directory Structure (項目目錄結構)

```
persona-friction-engine/
├── schemas/
│   ├── scenario.json              # Scenario Input Schema (輸入規範)
│   └── step_evaluation.json       # Step Evaluation Output Schema (輸出規範)
├── src/
│   ├── persona/                   # Persona cognitive profiling (畫像引擎)
│   ├── navigation/                # Playwright browser automation (導航引擎)
│   ├── evaluation/                # LLM Vision & CLS calculation (評估引擎)
│   ├── reporting/                 # HTML/CSS report generation (報告引擎)
│   └── orchestrator/              # Main loop & error recovery (協調器)
└── tests/                         # Full unit & integration tests (測試套件)
```

Enjoy building friction-free user experiences! 🚀
祝您打造出完美無瑕的用戶體驗！🚀
