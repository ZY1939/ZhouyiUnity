"""
用户配置管理器 — 负责加载/保存 usrCfg/UsrCfg.json 配置文件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【这个文件做什么】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  这是整个应用的"配置中心"。所有需要持久化的设置（AI 配置、外观、真太阳时等）
  都通过这个类来读写。它不是 QWidget，是一个纯数据管理类。

  核心概念：
    - 配置文件在磁盘上：usrCfg/UsrCfg.json（JSON 格式）
    - 内存中有一个 config_manager 对象（单例，全局唯一）
    - 调用 config_manager.get() 读取，config_manager.set() 写入
    - 每次 set() 自动保存到磁盘，并在控制台打印变更日志

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【配置结构】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  usrCfg/UsrCfg.json 是一个嵌套字典，结构如下：

  {
    "ai": {
      "active_provider": "deepseek",          ← 当前使用的 AI 服务
      "providers": {
        "lmstudio": {
          "base_url": "http://localhost:1234/v1",
          "model": "llama-3-8b"
        },
        "deepseek": {
          "api_key": "sk-xxxxx",
          "base_url": "https://api.deepseek.com",
          "model": "deepseek-v4-pro"
        }
      }
    },
    "appearance": {
      "background_color": "#f5f5f5",
      "background_image": "/path/to/bg.png",
      "font_family": "PingFang SC",
      "font_size": 16,
      "line_spacing": 1.5
    },
    "solar_time": {
      "enabled": false,
      "auto_locate_on_startup": true,
      "manual_edit": false,
      "city_name": "中国 北京 北京",
      "longitude": 116.4,
      "latitude": 39.9,
      "use_in_bazi": true,
      "show_in_statusbar": true
    }
  }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【使用示例】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 任何文件中，导入全局单例
  from ..config_manager import config_manager

  # ── 读取配置 ──
  font_size = config_manager.get("appearance", "font_size")     # 返回 16
  model = config_manager.get("ai", "providers", "deepseek", "model")  # 多级路径
  not_exist = config_manager.get("ai", "xxx")  # 路径不存在 → 返回 None

  # ── 写入配置（自动保存 + 控制台日志）──
  config_manager.set("appearance", "font_size", value=20)       # 改字号
  config_manager.set("solar_time", "enabled", value=True)       # 启用真太阳时

  # ── 手动保存（通常不需要，set() 自动保存）──
  config_manager.save()

  # ── 获取原始字典（只读）──
  all_data = config_manager.data  # 返回整个配置 dict

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【首次启动】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  如果 usrCfg/UsrCfg.json 不存在（程序第一次运行）：
    1. 自动创建 usrCfg 目录
    2. 生成默认配置（包含平台适配的字体）
    3. 检查环境变量 ANTHROPIC_AUTH_TOKEN，如有则预填 DeepSeek API Key
    4. 写入 UsrCfg.json

  这样用户安装后不需要手动创建配置文件。
"""
import json
import os
import platform

# ── 配置文件的存储路径 ──────────────────────────────────
# os.path.dirname(__file__) 获取本文件所在目录
# ".." 向上一级，".." 再向上一级（settings → src → ZhouyiUnity根目录）
# 最终得到: ZhouyiUnity/usrCfg/UsrCfg.json
_CFG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "usrCfg")
_CFG_PATH = os.path.join(_CFG_DIR, "UsrCfg.json")


def _default_font() -> str:
    """
    根据当前操作系统返回推荐的默认中文字体

    参数:
        （无参数，自动检测操作系统）

    返回:
        str: 字体名称
             - macOS (Darwin):  "PingFang SC"（苹方，系统自带）
             - Windows:         "Microsoft YaHei"（微软雅黑，系统自带）
             - 其他(Linux等):   "Noto Sans CJK SC"（思源黑体）

    用法:
        >>> _default_font()
        'PingFang SC'   # 在 Mac 上
    """
    system = platform.system()
    if system == "Darwin":
        return "PingFang SC"
    elif system == "Windows":
        return "Microsoft YaHei"
    else:
        return "Noto Sans CJK SC"


# ── 默认配置模板 ──────────────────────────────────────
# 首次运行时，如果 usrCfg/UsrCfg.json 不存在，就用这个生成默认文件
DEFAULT_CONFIG = {
    "ai": {
        "active_provider": "none",
        "providers": {
            "lmstudio": {
                "base_url": "http://localhost:1234/v1",
                "model": "",
                "timeout": 120,
            },
            "deepseek": {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-pro",
                "timeout": 30,
            },
            "custom": {
                "api_key": "",
                "base_url": "",
                "model": "",
                "timeout": 60,
            },
        },
    },
    "appearance": {
        "background_color": "#f5f5f5",
        "background_image": "",
        "background_image_mode": "fill",
        "background_image_opacity": 100,
        "font_family": _default_font(),
        "font_size": 16,
        "line_spacing": 1.5,
    },
    "solar_time": {
        "enabled": False,
        "auto_locate_on_startup": True,
        "manual_edit": False,
        "city_name": "",
        "longitude": 120.0,
        "latitude": 30.0,
        "use_in_bazi": True,
        "show_in_statusbar": True,
    },
    "general": {
        "last_tab_index": 4,  # 默认启动显示"设置"标签页
    },
}


class ConfigManager:
    """
    用户配置管理器

    生命周期：
      - 模块底部创建全局实例 config_manager = ConfigManager()
      - 构造时自动加载已有配置，或生成默认配置（首次启动）
      - 每次 set() 调用自动写入磁盘
    """

    def __init__(self):
        """
        构造 ConfigManager 实例

        参数:
            （无参数，自动从磁盘加载配置）

        做的事:
            1. 确保 usrCfg 目录存在
            2. 如果 UsrCfg.json 已存在 → 加载
            3. 如果不存在（首次启动）→ 生成默认配置 + 预填环境变量 + 保存
        """
        self._config = None  # 内存中的配置字典
        self._load()

    def _load(self):
        """
        （内部方法）加载配置文件，不存在则创建默认配置

        不直接调用此方法，它只在 __init__ 时自动执行一次。
        """
        os.makedirs(_CFG_DIR, exist_ok=True)
        if os.path.exists(_CFG_PATH):
            with open(_CFG_PATH, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            # 首次启动 → 深拷贝默认配置（避免引用污染）
            self._config = _deepcopy_default()
            self._prefill_from_env()
            self._save()

    def _prefill_from_env(self):
        """
        （内部方法）从环境变量预填 API 密钥

        如果系统环境变量中有 ANTHROPIC_AUTH_TOKEN，自动填入 DeepSeek 的 api_key，
        并将 active_provider 设为 "deepseek"。
        这样开发者不需要手动输入密钥。
        """
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        if token:
            self._config["ai"]["providers"]["deepseek"]["api_key"] = token
            self._config["ai"]["active_provider"] = "deepseek"

    def _save(self):
        """
        （内部方法）将当前配置写入磁盘

        写入 usrCfg/UsrCfg.json，JSON 格式，UTF-8 编码，缩进 2 空格。
        如果目录不存在会自动创建。
        """
        os.makedirs(_CFG_DIR, exist_ok=True)
        with open(_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def save(self):
        """
        手动保存配置到磁盘（公开接口）

        参数: （无）
        返回: None

        通常不需要手动调用，因为 set() 已经自动保存了。
        只在特殊场景（如外部需要强制同步磁盘）使用。

        用法:
            config_manager.save()
        """
        self._save()

    def get(self, *keys):
        """
        读取配置值，支持多级嵌套路径

        参数:
            *keys (str): 逐级向下的 key 路径，可以是 1 到 N 个
                         例: get("appearance")              → 返回整个外观配置字典
                             get("appearance", "font_size") → 返回字号数值
                             get("ai", "providers", "deepseek", "model") → 返回模型名

        返回:
            对应路径的值（可能是 dict / str / int / float / bool）
            如果路径中的任何一级不存在，返回 None（不会报错）

        用法:
            >>> config_manager.get("appearance", "font_size")
            16
            >>> config_manager.get("appearance", "xxx")
            None    # 不存在的 key 返回 None
        """
        val = self._config
        for k in keys:
            if not isinstance(val, dict):
                return None  # 中间路径不是字典 → 无法继续
            val = val.get(k)
        return val

    def set(self, *keys, value):
        """
        写入配置值，支持多级嵌套路径（自动保存 + 控制台日志）

        参数:
            *keys (str): 逐级向下的 key 路径，最后一级是要设置的值所在的 key
                         例: set("appearance", "font_size", value=20)
                             set("ai", "providers", "deepseek", "model", value="deepseek-chat")
            value: 要设置的值，类型任意（str / int / float / bool / dict 等）

        返回: None

        行为:
            - 中间路径不存在时会自动创建空字典
            - 写入后自动调用 _save() 落盘
            - 如果新旧值不同，控制台打印: [配置变更] path: 旧值 → 新值

        用法:
            >>> config_manager.set("appearance", "font_size", value=20)
            [配置变更] appearance.font_size: 16 → 20

            >>> config_manager.set("solar_time", "enabled", value=True)
            [配置变更] solar_time.enabled: False → True
        """
        target = self._config
        # 逐级进入，中间不存在的层级用 setdefault 创建空字典
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        old_val = target.get(keys[-1])
        target[keys[-1]] = value
        self._save()
        if old_val != value:
            path = ".".join(keys)
            print(f"[配置变更] {path}: {repr(old_val)} → {repr(value)}")

    @property
    def data(self):
        """
        返回原始配置字典的只读引用

        参数: （无，这是一个属性，不是方法）
        返回: dict — 完整的配置字典

        ⚠️ 不要直接修改返回值中的内容，请使用 set() 方法，
           否则修改不会被写入磁盘。

        用法:
            >>> config_manager.data
            {'ai': {'active_provider': 'deepseek', ...}, 'appearance': {...}, ...}
        """
        return self._config


def _deepcopy_default():
    """
    （模块级函数）深拷贝默认配置字典

    参数: （无）
    返回: dict — DEFAULT_CONFIG 的深拷贝

    为什么需要深拷贝：
        json.loads(json.dumps(...)) 生成的是全新的字典和嵌套对象。
        如果直接用 DEFAULT_CONFIG，后续修改会污染模板，
        导致第二次"首次启动"时的配置不干净。
    """
    return json.loads(json.dumps(DEFAULT_CONFIG))


# ── 全局单例 ────────────────────────────────────────────
# 模块首次被 import 时创建（Python 模块只会导入一次）
# 此后整个程序的所有文件 import 的 config_manager 都是同一个实例
config_manager = ConfigManager()
