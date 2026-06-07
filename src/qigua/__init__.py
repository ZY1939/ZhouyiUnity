"""
起卦工具包 — 手工指定 / 三位数 / 金钱卦 / 蓍草卦

导出清单：
    QiguaPanel          — 起卦主面板（整合卦图 + 输入 + 结果，供 yijing_viewer 调用）
    GuaResult           — 起卦结果 dataclass
    save_case / load_cases / get_case / delete_case / clear_cases — 案例存储管理
"""
from .divination_panel import QiguaPanel
from .bagua import GuaResult
from .case_manager import save_case, load_cases, get_case, delete_case, clear_cases
