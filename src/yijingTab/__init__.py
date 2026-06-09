"""
易经Tab — 起卦 + 算卦面板

导出清单：
    QiguaPanel          — 起卦主面板（整合卦图 + 输入 + 结果，供 yijing_viewer 调用）
    GuaResult           — 起卦结果 dataclass
    save_case / load_cases / get_case / delete_case / clear_cases — 案例存储管理
"""
from .qigua.divination_panel import QiguaPanel
from .com.bagua import GuaResult
from .qigua.case_manager import save_case, load_cases, get_case, delete_case, clear_cases
