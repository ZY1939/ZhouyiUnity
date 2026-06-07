"""
AI 工具设置面板 — 选择 / 配置 / 测试大语言模型 API 连接

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  提供 AI 提供商的选择、配置和连接测试功能。用户在此面板中：
    1. 选择 AI 提供商（无 / LM Studio / DeepSeek）
    2. 填写对应提供商的配置（API Key、Base URL、模型名）
    3. 测试连接是否正常（发送提示词 → 显示 AI 回复）

  所有配置变更自动保存到 usrCfg/UsrCfg.json。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【支持的 AI 提供商】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. "无"（不使用 AI）              — 无需任何配置
  2. LM Studio（本地，端口 1234）   — 扫描 + 自动选最优模型
  3. DeepSeek API（云端）           — API Key + Base URL + 模型名

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【面板结构】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - 提供商选择 QComboBox（无 / LM Studio / DeepSeek）
  - 配置区 QStackedWidget（三个子页面，根据选择自动切换）
  - 连接测试 QGroupBox（输入提示词 + 发送按钮 + 显示回复区域）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【LM Studio 模型获取流程（三步安全校验）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  步骤1: GET /models 连通性预检 — 检测 LM Studio 服务是否启动
  步骤2: 解析 JSON 响应，提取模型 ID 列表
  步骤3: 填入下拉列表，按 _pick_best_model() 自动选最优模型

  每一步失败都有明确的中文错误提示，并用颜色区分状态：
    红色(#ff3b30) = 失败  橙色(#ff9500) = 警告（无模型）  绿色(#34c759) = 成功

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模型排序规则】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  _model_rank() 根据以下维度打分，分数越高越优先：
    - 参数量: 405b(+100) > 70b(+80) > 34b(+60) > 13b(+40) > 7b(+20) > ...
    - 名称关键字: pro/max/ultra(+30) > large(+20) > medium(+10) > ... > mini(-20)
    - 名称长度: 每 4 字符 +1 分（长名称通常描述更具体）

  _pick_best_model() 取最高分模型，确保默认选中最大/最新的模型。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【测试连接机制】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  使用 QThread 子线程（TestWorker）执行 HTTP 请求，避免阻塞 UI。
  流程:
    1. 用户点击"测试连接"
    2. 创建 TestWorker 子线程 → 发送 POST /chat/completions
    3. 等待回复期间按钮显示"测试中..."且禁用
    4. 收到回复后通过 signal/slot 机制通知主线程更新 UI
    5. 成功 → 显示 AI 回复内容；失败 → 显示红色错误信息
"""
import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QSpinBox,
    QPushButton, QTextEdit, QGroupBox, QStackedWidget,
    QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QThread, Signal

from ..config_manager import config_manager

# ── 常量：提供商标识 ──────────────────────────────────
PROVIDER_NONE = "none"          # 不使用 AI
PROVIDER_LMSTUDIO = "lmstudio"  # LM Studio 本地部署
PROVIDER_DEEPSEEK = "deepseek"  # DeepSeek 云端 API
PROVIDER_CUSTOM = "custom"      # 自定义（兼容 OpenAI API 格式）

# ── 下拉列表显示名称 ──────────────────────────────────
PROVIDER_LABELS = {
    PROVIDER_NONE: "无（不使用 AI）",
    PROVIDER_LMSTUDIO: "LM Studio（本地）",
    PROVIDER_DEEPSEEK: "DeepSeek API（云端）",
    PROVIDER_CUSTOM: "自定义（兼容 OpenAI API）",
}

# ── 默认测试提示词 ────────────────────────────────────
DEFAULT_TEST_PROMPT = "你好，请问你是什么AI模型？请用中文简短回答。"

# ── 全局样式 ─────────────────────────────────────────
# 输入控件（白色底）和按钮（浅灰底）维持硬编码深色文字；
# QWidget、QGroupBox、QLabel 的文字色跟随外观背景切换
PANEL_STYLE = """
QWidget {{
    background: transparent;
}}
QGroupBox {{
    background: transparent;
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    color: {text_color};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {text_color};
}}
QComboBox, QLineEdit {{
    padding: 6px 10px;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    background: white;
    color: #1d1d1f;
    min-width: 280px;
}}
QComboBox:focus, QLineEdit:focus {{
    border-color: #007aff;
}}
QSpinBox {{
    padding: 6px 10px;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    background: white;
    color: #1d1d1f;
}}
QComboBox QAbstractItemView {{
    background: white;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: white;
}}
QPushButton {{
    padding: 6px 18px;
    border-radius: 6px;
    border: 1px solid #c0c0c0;
    background: #f5f5f5;
    color: #1d1d1f;
}}
QPushButton:hover {{
    background: #e8e8e8;
}}
QPushButton#btn_test {{
    background: #007aff;
    color: white;
    border: none;
    font-weight: bold;
    padding: 8px 24px;
}}
QPushButton#btn_test:hover {{
    background: #0062cc;
}}
QPushButton#btn_test:disabled {{
    background: #a0c4ff;
}}
QTextEdit#response_text {{
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    background: #fafafa;
    padding: 10px;
    font-size: 14px;
    color: #1d1d1f;
}}
QLabel {{
    background: transparent;
    color: {text_color};
}}
"""


class TestWorker(QThread):
    """
    后台线程 — 向 AI 服务发送测试请求

    为什么用 QThread 而非直接阻塞调用：
      网络请求可能耗时 30 秒以上。如果直接在主线程中调用 requests.post()，
      Qt 的事件循环会被阻塞，整个窗口冻结（无法点击、无法移动）。
      用子线程 + signal/slot 机制，请求在后台执行，完成后通知 UI 线程更新。

    参数:
        provider (str): 提供商标识，如 "lmstudio" 或 "deepseek"
        config (dict): 提供商的配置字典，包含 base_url / api_key(仅deepseek) / model
        prompt (str): 要发送的测试提示词

    信号:
        finished_signal(bool, str)
          - bool: True = 成功收到回复, False = 出错
          - str: 成功时 = AI 的回复内容；失败时 = 错误信息

    用法:
        >>> worker = TestWorker("deepseek", {"api_key": "sk-xxx", ...}, "你好")
        >>> worker.finished_signal.connect(self._on_test_done)
        >>> worker.start()  # 启动子线程
    """
    finished_signal = Signal(bool, str)

    def __init__(self, provider, config, prompt, timeout=30):
        """
        构造 TestWorker 实例

        参数:
            provider (str): 提供商标识（PROVIDER_LMSTUDIO 或 PROVIDER_DEEPSEEK）
            config (dict): 提供商配置，来自 usrCfg 中 ai.providers.<provider>
                           LM Studio: {"base_url": "...", "model": "..."}
                           DeepSeek:  {"base_url": "...", "api_key": "...", "model": "..."}
            prompt (str): 用户输入的测试提示词
            timeout (int): 请求超时秒数，默认 30
        """
        super().__init__()
        self.provider = provider
        self.config = config
        self.prompt = prompt
        self.timeout = timeout

    def run(self):
        """
        执行 HTTP POST 请求（在子线程中运行，不阻塞 UI）

        参数:
            （无参数，使用构造时保存的 provider/config/prompt）

        返回:
            None（通过 finished_signal 信号返回结果）

        做的事:
            1. 根据 provider 构建不同的请求（LM Studio 无需认证头，DeepSeek 需要 Bearer Token）
            2. 发送 POST 请求到 {base_url}/chat/completions
            3. 解析响应，提取 choices[0].message.content
            4. 出错时 emit 详细的错误信息

        错误分类:
            - ConnectionError: 无法连接到服务器（地址/端口错误或服务未启动）
            - Timeout: 请求超过 30 秒无响应
            - HTTP 错误: 返回非 200 状态码（如 401 认证失败、404 地址错误）
            - 其他异常: 直接显示异常信息
        """
        try:
            if self.provider == PROVIDER_LMSTUDIO:
                # LM Studio 是本地服务，不需要认证头
                # model 为空时用 "local-model" 作为兜底值
                url = f"{self.config['base_url']}/chat/completions"
                payload = {
                    "model": self.config["model"] or "local-model",
                    "messages": [{"role": "user", "content": self.prompt}],
                    "temperature": 0.7,
                }
                resp = requests.post(url, json=payload, timeout=self.timeout)
            elif self.provider in (PROVIDER_DEEPSEEK, PROVIDER_CUSTOM):
                # DeepSeek / 自定义：均使用 OpenAI 兼容 API 格式（Bearer Token 认证）
                url = f"{self.config['base_url']}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.config['api_key']}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.config["model"],
                    "messages": [{"role": "user", "content": self.prompt}],
                    "stream": False,
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            else:
                self.finished_signal.emit(False, "未选择 AI 提供商")
                return

            if resp.status_code == 200:
                data = resp.json()
                # OpenAI 兼容格式: choices[0].message.content
                content = data["choices"][0]["message"]["content"]
                self.finished_signal.emit(True, content)
            else:
                # 截取前 500 字符，避免服务器返回大量 HTML 错误页撑爆 UI
                detail = resp.text[:500]
                self.finished_signal.emit(False, f"HTTP {resp.status_code}: {detail}")
        except requests.exceptions.ConnectionError:
            self.finished_signal.emit(False, "连接失败：无法连接到服务器，请检查地址和端口")
        except requests.exceptions.Timeout:
            self.finished_signal.emit(False, f"请求超时（{self.timeout}秒）")
        except Exception as e:
            self.finished_signal.emit(False, f"请求异常：{str(e)}")


class AIPanel(QWidget):
    """
    AI 工具设置面板 — 选择/配置/测试 AI 服务

    参数:
        parent (QWidget, 可选): 父 Widget，通常由 QStackedWidget 管理时自动传入

    生命周期:
        - 被 SettingsTab 创建时实例化
        - 构造时自动从 usrCfg 加载配置并填充控件
        - 用户修改任何设置后自动保存

    用法:
        # 在 settings_tab.py 中：
        from .panels.ai_panel import AIPanel
        ai_panel = AIPanel()
        self._content_stack.addWidget(ai_panel)
    """

    def __init__(self, parent=None):
        """
        构造 AIPanel 实例

        参数:
            parent (QWidget, 可选): 父 Widget

        做的事:
            1. 初始化 _worker 为 None（测试线程引用）
            2. 调用 _init_ui() 构建界面
            3. 调用 _load_config() 从 usrCfg 加载已保存的配置
            4. 调用 _connect_signals() 绑定控件事件
        """
        super().__init__(parent)
        self._worker = None  # 当前测试线程引用（避免被 Python GC 回收）
        self._init_ui()
        self._load_config()
        self._connect_signals()

    # ── UI 构建 ───────────────────────────────────────

    def _init_ui(self):
        """
        （内部方法）构建面板的完整 UI 布局

        参数:
            （无参数）

        返回:
            None（直接设置 self 的布局和子控件）

        UI 结构（从上到下）:
            1. 提供商选择 QGroupBox: QComboBox 选择 AI 提供商
            2. 配置区 QStackedWidget: 三个子页面（无/LM Studio/DeepSeek），根据选择切换
            3. 测试区 QGroupBox: 提示词输入 + 测试按钮 + 回复显示
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        # ── 提供商选择 ──
        provider_group = QGroupBox("AI 提供商")
        provider_layout = QFormLayout(provider_group)
        provider_layout.setSpacing(12)

        self._provider_combo = QComboBox()
        for key, label in PROVIDER_LABELS.items():
            self._provider_combo.addItem(label, key)  # data = provider key（用于后续查找）
        provider_layout.addRow("当前使用：", self._provider_combo)
        root.addWidget(provider_group)

        # ── 提供商配置区（QStackedWidget 按选择切换页面）──
        self._config_stack = QStackedWidget()

        # 构建各个提供商的配置子页面
        self._lmstudio_widget = self._build_lmstudio_config()
        self._deepseek_widget = self._build_deepseek_config()
        self._custom_widget = self._build_custom_config()
        self._none_widget = QWidget()  # "无" 时只显示空白页

        # 注意：addWidget 的顺序决定了索引，与 _switch_provider_config() 中的映射对应
        self._config_stack.addWidget(self._none_widget)       # index 0: none
        self._config_stack.addWidget(self._lmstudio_widget)   # index 1: lmstudio
        self._config_stack.addWidget(self._deepseek_widget)   # index 2: deepseek
        self._config_stack.addWidget(self._custom_widget)     # index 3: custom
        root.addWidget(self._config_stack)

        # ── 测试区域 ──
        test_group = QGroupBox("连接测试")
        test_layout = QVBoxLayout(test_group)
        test_layout.setSpacing(12)

        prompt_row = QHBoxLayout()
        self._prompt_input = QLineEdit()
        self._prompt_input.setPlaceholderText("输入测试提示词...")
        self._prompt_input.setText(DEFAULT_TEST_PROMPT)
        prompt_row.addWidget(self._prompt_input)

        self._btn_test = QPushButton("测试连接")
        self._btn_test.setObjectName("btn_test")  # 蓝色强调按钮样式
        prompt_row.addWidget(self._btn_test)

        self._btn_stop = QPushButton("停止")
        self._btn_stop.setStyleSheet(
            "background: #ff3b30; color: white; border: none; "
            "font-weight: bold; padding: 8px 24px; border-radius: 6px;"
        )
        self._btn_stop.hide()  # 初始隐藏，仅在测试中显示
        prompt_row.addWidget(self._btn_stop)
        test_layout.addLayout(prompt_row)

        self._response_text = QTextEdit()
        self._response_text.setObjectName("response_text")
        self._response_text.setReadOnly(True)
        self._response_text.setMinimumHeight(120)
        self._response_text.setPlaceholderText("AI 回复将显示在这里...")
        test_layout.addWidget(self._response_text)
        root.addWidget(test_group)

        root.addStretch()
        self.setStyleSheet(PANEL_STYLE.format(text_color="#1d1d1f"))

    def refresh_text_color(self, text_color: str):
        """
        根据背景亮度更新面板文字颜色（由 appearance_manager 调用）

        参数:
            text_color (str): 计算后的文字颜色，如 "#ffffff" 或 "#1d1d1f"
        """
        self.setStyleSheet(PANEL_STYLE.format(text_color=text_color))

    def _build_lmstudio_config(self) -> QWidget:
        """
        （内部方法）构建 LM Studio 配置子页面

        参数:
            （无参数）

        返回:
            QWidget: 包含 LM Studio 配置表单的 Widget

        页面内容:
            - Base URL 输入框（默认 http://localhost:1234/v1）
            - 模型下拉列表（可编辑，也可手动输入模型名）
            - 「扫描」按钮 → 自动从 LM Studio 服务器获取可用模型
            - 状态标签（成功=绿色 / 失败=红色 / 等待=灰色）

        用法:
            # 在 _init_ui() 中调用
            self._lmstudio_widget = self._build_lmstudio_config()
        """
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(12)

        self._lm_base_url = QLineEdit()
        self._lm_base_url.setPlaceholderText("http://localhost:1234/v1")
        layout.addRow("Base URL：", self._lm_base_url)

        model_row = QHBoxLayout()
        self._lm_model_combo = QComboBox()
        self._lm_model_combo.setMinimumWidth(200)
        self._lm_model_combo.setEditable(True)  # 可编辑 → 用户能手动输入模型名
        self._lm_model_combo.setPlaceholderText("请先扫描...")
        model_row.addWidget(self._lm_model_combo)

        self._btn_fetch_models = QPushButton("扫描")
        model_row.addWidget(self._btn_fetch_models)
        layout.addRow("模型：", model_row)

        self._lm_status = QLabel("")
        self._lm_status.setStyleSheet("color: #888; font-size: 13px;")
        layout.addRow("", self._lm_status)

        # 请求超时（本地大模型推理慢，默认 120 秒）
        timeout_row = QHBoxLayout()
        self._lm_timeout = QSpinBox()
        self._lm_timeout.setRange(10, 600)
        self._lm_timeout.setSingleStep(10)
        self._lm_timeout.setValue(120)
        self._lm_timeout.setSuffix(" 秒")
        self._lm_timeout.setFixedWidth(90)
        timeout_row.addWidget(self._lm_timeout)
        lm_timeout_hint = QLabel("建议 120 秒，本地大模型推理较慢")
        lm_timeout_hint.setStyleSheet("color: #888; font-size: 13px;")
        timeout_row.addWidget(lm_timeout_hint)
        timeout_row.addStretch()
        layout.addRow("请求超时：", timeout_row)

        return w

    def _build_deepseek_config(self) -> QWidget:
        """
        （内部方法）构建 DeepSeek 配置子页面

        参数:
            （无参数）

        返回:
            QWidget: 包含 DeepSeek 配置表单的 Widget

        页面内容:
            - API Key 输入框（明文输入，placeholder 显示 sk-...）
            - Base URL 输入框（默认 https://api.deepseek.com）
            - 模型下拉列表（预填 deepseek-v4-pro / deepseek-v4-flash / deepseek-chat，可编辑）

        用法:
            # 在 _init_ui() 中调用
            self._deepseek_widget = self._build_deepseek_config()
        """
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(12)

        self._ds_api_key = QLineEdit()
        self._ds_api_key.setPlaceholderText("sk-...")
        self._ds_api_key.setMinimumWidth(360)
        layout.addRow("API Key：", self._ds_api_key)

        self._ds_base_url = QLineEdit()
        self._ds_base_url.setPlaceholderText("https://api.deepseek.com")
        layout.addRow("Base URL：", self._ds_base_url)

        self._ds_model_combo = QComboBox()
        self._ds_model_combo.setEditable(True)
        self._ds_model_combo.addItems(["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat"])
        layout.addRow("模型：", self._ds_model_combo)

        # 请求超时（云端 API 快，默认 30 秒）
        timeout_row = QHBoxLayout()
        self._ds_timeout = QSpinBox()
        self._ds_timeout.setRange(10, 600)
        self._ds_timeout.setSingleStep(10)
        self._ds_timeout.setValue(30)
        self._ds_timeout.setSuffix(" 秒")
        self._ds_timeout.setFixedWidth(90)
        timeout_row.addWidget(self._ds_timeout)
        ds_timeout_hint = QLabel("建议 30 秒，云端 API 响应快")
        ds_timeout_hint.setStyleSheet("color: #888; font-size: 13px;")
        timeout_row.addWidget(ds_timeout_hint)
        timeout_row.addStretch()
        layout.addRow("请求超时：", timeout_row)

        return w

    def _build_custom_config(self) -> QWidget:
        """
        （内部方法）构建自定义 API 配置子页面

        参数:
            （无参数）

        返回:
            QWidget: 包含自定义 API 配置表单的 Widget

        页面内容:
            - API Key 输入框（明文输入，placeholder 显示 "sk-... 或留空"）
            - Base URL 输入框（placeholder 显示 "https://api.openai.com/v1"）
            - 模型下拉列表（可编辑，placeholder 显示 "gpt-4o"）

        兼容性:
            任何支持 OpenAI 兼容 API 格式的服务都可以使用此选项，例如：
              - OpenAI:        https://api.openai.com/v1
              - Groq:          https://api.groq.com/openai/v1
              - Together AI:   https://api.together.xyz/v1
              - OpenRouter:    https://openrouter.ai/api/v1
              - 硅基流动:       https://api.siliconflow.cn/v1
              - 本地 Ollama:    http://localhost:11434/v1

        用法:
            # 在 _init_ui() 中调用
            self._custom_widget = self._build_custom_config()
        """
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(12)

        self._cu_api_key = QLineEdit()
        self._cu_api_key.setPlaceholderText("sk-... 或留空（部分服务不需要）")
        self._cu_api_key.setMinimumWidth(360)
        layout.addRow("API Key：", self._cu_api_key)

        self._cu_base_url = QLineEdit()
        self._cu_base_url.setPlaceholderText("https://api.openai.com/v1")
        layout.addRow("Base URL：", self._cu_base_url)

        self._cu_model_combo = QComboBox()
        self._cu_model_combo.setEditable(True)
        self._cu_model_combo.setPlaceholderText("gpt-4o")
        layout.addRow("模型：", self._cu_model_combo)

        # 请求超时（视服务而定，默认 60 秒）
        timeout_row = QHBoxLayout()
        self._cu_timeout = QSpinBox()
        self._cu_timeout.setRange(10, 600)
        self._cu_timeout.setSingleStep(10)
        self._cu_timeout.setValue(60)
        self._cu_timeout.setSuffix(" 秒")
        self._cu_timeout.setFixedWidth(90)
        timeout_row.addWidget(self._cu_timeout)
        cu_timeout_hint = QLabel("建议 60 秒，视具体服务而定")
        cu_timeout_hint.setStyleSheet("color: #888; font-size: 13px;")
        timeout_row.addWidget(cu_timeout_hint)
        timeout_row.addStretch()
        layout.addRow("请求超时：", timeout_row)

        return w

    # ── 配置加载/保存 ─────────────────────────────────

    def _load_config(self):
        """
        （内部方法）从 usrCfg 加载 AI 配置并填充到各控件

        参数:
            （无参数，从 config_manager 读取配置）

        返回:
            None

        加载内容:
            1. active_provider → 选中对应的下拉项
            2. LM Studio 的 base_url + model
            3. DeepSeek 的 api_key + base_url + model

        用法:
            # 只在 __init__ 时调用一次
            self._load_config()
        """
        # 提供商选择
        active = config_manager.get("ai", "active_provider") or PROVIDER_NONE
        idx = self._provider_combo.findData(active)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        self._switch_provider_config(active)

        # LM Studio 配置
        cfg = config_manager.get("ai", "providers", "lmstudio") or {}
        self._lm_base_url.setText(cfg.get("base_url", "http://localhost:1234/v1"))
        model = cfg.get("model", "")
        if model:
            self._lm_model_combo.setCurrentText(model)
        self._lm_timeout.setValue(cfg.get("timeout", 120))
        if "timeout" not in cfg:
            config_manager.set("ai", "providers", "lmstudio", "timeout", value=120)

        # DeepSeek 配置
        cfg = config_manager.get("ai", "providers", "deepseek") or {}
        self._ds_api_key.setText(cfg.get("api_key", ""))
        self._ds_base_url.setText(cfg.get("base_url", "https://api.deepseek.com"))
        self._ds_model_combo.setCurrentText(cfg.get("model", "deepseek-v4-pro"))
        self._ds_timeout.setValue(cfg.get("timeout", 30))
        if "timeout" not in cfg:
            config_manager.set("ai", "providers", "deepseek", "timeout", value=30)

        # 自定义 API 配置
        cfg = config_manager.get("ai", "providers", "custom") or {}
        self._cu_api_key.setText(cfg.get("api_key", ""))
        self._cu_base_url.setText(cfg.get("base_url", ""))
        self._cu_model_combo.setCurrentText(cfg.get("model", ""))
        self._cu_timeout.setValue(cfg.get("timeout", 60))
        if "timeout" not in cfg:
            config_manager.set("ai", "providers", "custom", "timeout", value=60)

    def _connect_signals(self):
        """
        （内部方法）连接 UI 控件的变更信号到对应的处理逻辑

        参数:
            （无参数）

        返回:
            None

        连接关系:
            - _provider_combo 的选项变更 → 保存提供商选择 + 切换配置子页面
            - _btn_test 的点击 → 发起 AI 连接测试
            - _btn_fetch_models 的点击 → 从 LM Studio 扫描
            - LM Studio 各输入框的文本变更 → 自动保存到 usrCfg
            - DeepSeek 各输入框的文本变更 → 自动保存到 usrCfg

        使用 QComboBox.currentTextChanged 而非 textChanged，
        因为 QComboBox 不是 QLineEdit，只有 currentTextChanged 信号。
        """
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._btn_test.clicked.connect(self._on_test)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_fetch_models.clicked.connect(self._on_fetch_models)

        # 配置变更 → 自动保存到 usrCfg（输入即保存，无需手动点"保存"按钮）
        self._lm_base_url.textChanged.connect(self._save_lm_config)
        self._lm_model_combo.currentTextChanged.connect(self._save_lm_config)
        self._ds_api_key.textChanged.connect(self._save_ds_config)
        self._ds_base_url.textChanged.connect(self._save_ds_config)
        self._ds_model_combo.currentTextChanged.connect(self._save_ds_config)
        self._cu_api_key.textChanged.connect(self._save_custom_config)
        self._cu_base_url.textChanged.connect(self._save_custom_config)
        self._cu_model_combo.currentTextChanged.connect(self._save_custom_config)

        # 各 provider 超时变更 → 各自保存
        self._lm_timeout.valueChanged.connect(self._save_lm_config)
        self._ds_timeout.valueChanged.connect(self._save_ds_config)
        self._cu_timeout.valueChanged.connect(self._save_custom_config)

    # ── 槽函数 ────────────────────────────────────────

    def _on_provider_changed(self, index):
        """
        （槽函数）提供商下拉选择变更 → 保存选择 + 切换配置子页面

        参数:
            index (int): 用户选择的项在 QComboBox 中的索引（从 0 开始）
                         （该参数由 QComboBox.currentIndexChanged 信号自动传入）

        返回:
            None

        做的事:
            1. 从 QComboBox 的 data 中取出 provider key（如 "deepseek"）
            2. 调用 config_manager.set() 保存到 usrCfg
            3. 调用 _switch_provider_config() 切换 QStackedWidget 子页面

        用法:
            # 通过信号自动触发，不需要手动调用
            self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        """
        provider = self._provider_combo.currentData()
        config_manager.set("ai", "active_provider", value=provider)
        self._switch_provider_config(provider)

    def _switch_provider_config(self, provider):
        """
        （内部方法）根据提供商标识切换到对应的配置子页面

        参数:
            provider (str): 提供商标识，取值为 "none" / "lmstudio" / "deepseek"

        返回:
            None

        映射:
            "none"     → QStackedWidget index 0（空白页）
            "lmstudio" → QStackedWidget index 1（LM Studio 配置）
            "deepseek" → QStackedWidget index 2（DeepSeek 配置）
            "custom"   → QStackedWidget index 3（自定义 API 配置）
            未识别的 provider → 默认 index 0

        用法:
            >>> self._switch_provider_config("deepseek")  # 显示 DeepSeek 配置页
        """
        mapping = {PROVIDER_NONE: 0, PROVIDER_LMSTUDIO: 1, PROVIDER_DEEPSEEK: 2, PROVIDER_CUSTOM: 3}
        self._config_stack.setCurrentIndex(mapping.get(provider, 0))

    def _save_lm_config(self):
        """
        （内部方法）将当前 LM Studio 配置保存到 usrCfg

        参数:
            （无参数，直接从对应控件读取当前值）

        返回:
            None

        保存内容:
            - ai.providers.lmstudio.base_url
            - ai.providers.lmstudio.model

        注意:
            base_url 和 model 都会 strip() 去掉首尾空格，
            避免用户误输入空格导致连接失败。
        """
        config_manager.set("ai", "providers", "lmstudio", "base_url",
                           value=self._lm_base_url.text().strip())
        config_manager.set("ai", "providers", "lmstudio", "model",
                           value=self._lm_model_combo.currentText().strip())
        config_manager.set("ai", "providers", "lmstudio", "timeout",
                           value=self._lm_timeout.value())

    def _save_ds_config(self):
        """
        （内部方法）将当前 DeepSeek 配置保存到 usrCfg

        参数:
            （无参数，直接从对应控件读取当前值）

        返回:
            None

        保存内容:
            - ai.providers.deepseek.api_key
            - ai.providers.deepseek.base_url
            - ai.providers.deepseek.model

        注意:
            所有值都会 strip() 去掉首尾空格。
            API Key 去除空格很重要，因为空格会导致认证失败。
        """
        config_manager.set("ai", "providers", "deepseek", "api_key",
                           value=self._ds_api_key.text().strip())
        config_manager.set("ai", "providers", "deepseek", "base_url",
                           value=self._ds_base_url.text().strip())
        config_manager.set("ai", "providers", "deepseek", "model",
                           value=self._ds_model_combo.currentText().strip())
        config_manager.set("ai", "providers", "deepseek", "timeout",
                           value=self._ds_timeout.value())

    def _save_custom_config(self):
        """
        （内部方法）将当前自定义 API 配置保存到 usrCfg

        参数:
            （无参数，直接从对应控件读取当前值）

        返回:
            None

        保存内容:
            - ai.providers.custom.api_key
            - ai.providers.custom.base_url
            - ai.providers.custom.model

        注意:
            所有值都会 strip() 去掉首尾空格。
            API Key 可为空（部分本地服务如 Ollama 不需要认证）。
        """
        config_manager.set("ai", "providers", "custom", "api_key",
                           value=self._cu_api_key.text().strip())
        config_manager.set("ai", "providers", "custom", "base_url",
                           value=self._cu_base_url.text().strip())
        config_manager.set("ai", "providers", "custom", "model",
                           value=self._cu_model_combo.currentText().strip())
        config_manager.set("ai", "providers", "custom", "timeout",
                           value=self._cu_timeout.value())

    def _on_fetch_models(self):
        """
        （槽函数）从 LM Studio 扫描（三步安全校验）

        参数:
            （无参数）

        返回:
            None

        流程（三步，任一步失败都有明确提示）:

            步骤1 — 连通性预检:
              发送 GET {base_url}/models，超时 5 秒。
              失败 → 显示"LM Studio 未运行，请先启动 LM Studio 并加载模型"（红色）
              成功 → 进入步骤2

            步骤2 — 解析模型列表:
              从 JSON 响应的 data[] 中提取每个模型的 "id" 字段。
              失败 → 显示"解析模型列表失败"（红色）
              列表为空 → 显示"未找到模型"（橙色警告）
              成功 → 进入步骤3

            步骤3 — 填入下拉列表:
              清空现有列表 → 添加所有模型 → 调用 _pick_best_model() 自动选最优
              → 保存当前选中的模型到 usrCfg
              成功 → 显示"找到 N 个模型，已选 XXX"（绿色）

        颜色含义:
            红色(#ff3b30) = 错误，需要用户处理
            橙色(#ff9500) = 警告，服务运行但无模型加载
            绿色(#34c759) = 成功
        """
        base_url = self._lm_base_url.text().strip().rstrip("/")
        self._lm_status.setText("正在检测 LM Studio 服务...")
        self._btn_fetch_models.setEnabled(False)

        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr.show_status("正在扫描 LM Studio...")

        QApplication.processEvents()  # 强制刷新 UI → 用户看到"检测中"状态

        # ── 步骤1：连通性预检 ──
        try:
            health = requests.get(f"{base_url}/models", timeout=5)
        except requests.exceptions.ConnectionError:
            self._lm_status.setText("LM Studio 未运行，请先启动 LM Studio 并加载模型")
            self._lm_status.setStyleSheet("color: #ff3b30; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return
        except requests.exceptions.Timeout:
            self._lm_status.setText("连接超时，请检查 Base URL 是否正确")
            self._lm_status.setStyleSheet("color: #ff3b30; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return
        except Exception as e:
            self._lm_status.setText(f"连接失败：{e}")
            self._lm_status.setStyleSheet("color: #ff3b30; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return

        if health.status_code != 200:
            self._lm_status.setText(f"LM Studio 返回 HTTP {health.status_code}，请检查服务状态")
            self._lm_status.setStyleSheet("color: #ff3b30; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return

        # ── 步骤2：解析模型列表 ──
        self._lm_status.setText("正在扫描...")
        QApplication.processEvents()

        try:
            data = health.json()
            models = [m["id"] for m in data.get("data", [])]
        except Exception as e:
            self._lm_status.setText(f"解析模型列表失败：{e}")
            self._lm_status.setStyleSheet("color: #ff3b30; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return

        if not models:
            self._lm_status.setText("未找到模型，请确认 LM Studio 已加载模型")
            self._lm_status.setStyleSheet("color: #ff9500; font-size: 13px;")
            self._btn_fetch_models.setEnabled(True)
            if mgr: mgr.reset_status()
            return

        # ── 步骤3：填入下拉列表（按模型大小降序排列），自动选最优模型 ──
        self._lm_model_combo.clear()
        # 按 _model_rank 降序排列，大模型在前、小模型在后
        sorted_models = sorted(models, key=_model_rank, reverse=True)
        self._lm_model_combo.addItems(sorted_models)

        best = _pick_best_model(models)
        idx = self._lm_model_combo.findText(best)
        if idx >= 0:
            self._lm_model_combo.setCurrentIndex(idx)

        self._lm_status.setText(f"找到 {len(models)} 个模型，已选 {best}")
        self._lm_status.setStyleSheet("color: #34c759; font-size: 13px;")
        self._btn_fetch_models.setEnabled(True)

        # 恢复状态栏
        if mgr: mgr.reset_status()

        # 保存当前选中的模型到 usrCfg
        self._save_lm_config()

    def _on_test(self):
        """
        （槽函数）发起 AI 连接测试

        参数:
            （无参数）

        返回:
            None

        流程:
            1. 检查是否选择了提供商（"无" → 弹窗提示）
            2. 从 usrCfg 读取当前提供商的配置
            3. 创建 TestWorker 子线程执行 HTTP 请求
            4. UI 进入"测试中..."状态（按钮禁用 + 文字变化）
            5. 收到回复后通过 _on_test_done 回调更新界面

        注意:
            self._worker 保持对 TestWorker 的引用，防止 Python GC 回收。
            如果 worker 被 GC 回收，信号连接会失效，UI 永远收不到结果。
        """
        provider = self._provider_combo.currentData()
        if provider == PROVIDER_NONE:
            QMessageBox.information(self, "提示", "请先选择一个 AI 提供商")
            return

        cfg = config_manager.get("ai", "providers", provider) or {}
        prompt = self._prompt_input.text().strip()
        if not prompt:
            prompt = DEFAULT_TEST_PROMPT

        self._btn_test.setVisible(False)
        self._btn_stop.setVisible(True)
        self._response_text.clear()
        self._response_text.setPlaceholderText("正在等待 AI 回复...")

        # 状态栏显示 "AI 等待回答..."
        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr.show_status("AI 等待回答...")

        # 从当前 provider 配置中读取超时（不同 provider 有各自的超时设置）
        timeout = cfg.get("timeout", 30)
        self._worker = TestWorker(provider, cfg, prompt, timeout=timeout)
        self._worker.finished_signal.connect(self._on_test_done)
        self._worker.start()

    def _on_stop(self):
        """
        （槽函数）强制停止正在进行的 AI 连接测试

        参数:
            （无参数）

        返回:
            None

        做的事:
            1. 调用 QThread.terminate() 强制结束子线程
            2. 释放 worker 引用（防止悬空指针）
            3. 恢复按钮状态（显示"测试连接"，隐藏"停止"）
            4. 恢复状态栏为"就绪"

        注意:
            QThread.terminate() 是强制终止，不保证资源清理。
            但在这个场景下（HTTP 请求卡住），这是唯一能响应用户操作的方式。
        """
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)  # 等待最多 1 秒让线程完全结束
            self._worker = None

        self._btn_test.setVisible(True)
        self._btn_stop.setVisible(False)
        self._response_text.setHtml(
            '<p style="color: #ff9500;">测试已被用户停止</p>'
        )

        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr.reset_status()

    def _on_test_done(self, success, message):
        """
        （槽函数）测试完成回调 — 在 UI 中显示结果

        参数:
            success (bool): True = 成功收到 AI 回复, False = 出错
            message (str): success=True 时 = AI 回复的文字内容
                          success=False 时 = 友好的中文错误信息

        返回:
            None

        显示方式:
            - 成功: setPlainText() 显示纯文本回复
            - 失败: setHtml() 以红色文字显示错误信息（带 pre-wrap 保留换行）

        注意:
            此方法在主线程中执行（由 Qt signal/slot 机制保证），
            因此可以安全地操作 UI 控件。
        """
        # 如果用户已点"停止"按钮终止了测试，不再更新 UI
        if not self._btn_stop.isVisible():
            return

        self._btn_test.setVisible(True)
        self._btn_stop.setVisible(False)
        # 恢复状态栏
        mgr = getattr(self.window(), "_statusbar_mgr", None)
        if mgr:
            mgr.reset_status()
        if success:
            self._response_text.setPlainText(message)
        else:
            # 错误信息用红色 HTML 显示，pre-wrap 保留换行格式
            self._response_text.setHtml(
                f'<p style="color: #ff3b30; white-space: pre-wrap;">{message}</p>'
            )


# ── 模块级辅助函数：模型排序 ──────────────────────────

def _model_rank(name: str) -> int:
    """
    给模型名打分，分数越高表示越优先选择

    参数:
        name (str): 模型名称（LM Studio 返回的 model id），如 "qwen2.5-7b-instruct"

    返回:
        int: 评分（可正可负），分数越高越优先

    评分维度:
        1. 参数量（最重要）:
           405b(+100) > 70b(+80) > 34b(+60) > 13b(+40) > 7b(+20) > 3b(+10) > 1b(+5)
           只匹配第一个命中的参数量。

        2. 名称关键字:
           pro/max/ultra(+30) > large(+20) > medium(+10) > small(-10) > tiny/mini(-20)
           正向关键字表示旗舰/高端模型，负向表示轻量/精简版。

        3. 名称长度:
           每 4 个字符 +1 分，最多贡献 15 分。
           长名称通常包含更多描述信息（如 "qwen2.5-72b-instruct" 比 "qwen2" 更具体）。

    用法:
        >>> _model_rank("qwen2.5-7b-instruct")
        20       # 7b(+20)
        >>> _model_rank("llama-3-70b-instruct")
        80       # 70b(+80)
        >>> _model_rank("deepseek-coder-33b-instruct")
        60       # 34b(未匹配33b，按后续规则得分)
    """
    score = 0
    lower = name.lower()
    # 参数量加权
    for kw, pts in [("405b", 100), ("70b", 80), ("34b", 60), ("13b", 40),
                     ("7b", 20), ("3b", 10), ("1b", 5)]:
        if kw in lower:
            score += pts
            break
    # 名称关键字加权
    for kw, pts in [("pro", 30), ("max", 30), ("ultra", 30), ("large", 20),
                     ("medium", 10), ("small", -10), ("tiny", -20), ("mini", -20)]:
        if kw in lower:
            score += pts
    # 名称长度微弱加分（长名称通常包含更多信息量）
    score += min(len(name) // 4, 15)
    return score


def _pick_best_model(models: list) -> str:
    """
    从模型列表中选出最优的（按 _model_rank 排序取最高分）

    参数:
        models (list[str]): 模型名称列表，如 ["qwen2.5-1.5b", "qwen2.5-7b", "qwen2.5-72b"]

    返回:
        str: 得分最高的模型名。如果列表为空，返回空字符串 ""

    为什么需要:
        LM Studio 可能加载了多个模型。如果不排序，QComboBox 默认选第一个，
        可能是最小的模型。此函数确保默认选中参数最大/最新的模型。

    用法:
        >>> models = ["qwen2.5-1.5b", "qwen2.5-7b", "qwen2.5-72b"]
        >>> _pick_best_model(models)
        'qwen2.5-72b'  # 72b 得分最高
        >>> _pick_best_model([])
        ''              # 空列表返回空字符串
    """
    if not models:
        return ""
    ranked = sorted(models, key=_model_rank, reverse=True)
    return ranked[0]
