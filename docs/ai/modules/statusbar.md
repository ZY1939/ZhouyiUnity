# 状态栏系统

> 最后更新：2026-06-08

---

## 显示格式

```
[就绪]                    时间(真) 14:30 (14:12) | 农历 | 四柱(真) | 小六壬
```

- 左侧：就绪标签 + `show_status(msg)` / `reset_status()` 状态消息
- 右侧：时间(真/平) 公历 (平太阳时) | 农历 | 四柱(真/平) | 小六壬掌诀

## 智能刷新

| 场景 | 刷新频率 |
|------|----------|
| 距时辰交界 ≤ 2分钟 | 每秒（快速） |
| 距时辰交界 > 2分钟 | 每 30 秒（慢速） |

- 时辰判断：`use_in_bazi` 勾选 → 真太阳时；否则 → 北京时间
- 配置变更后立即 `mgr._refresh()`，不等 timer

## 外观

- 跟随系统 Qt.ColorScheme（深色/浅色模式），不随设置面板背景
- 时间标签文本颜色联动 `appearance_manager` 的文字颜色

## 状态消息

```python
mgr = getattr(self.window(), "_statusbar_mgr", None)
mgr.show_status("<span style='color:#007aff;'>[Info] 消息</span>")  # 5秒自动恢复
mgr.reset_status()
```

- `_status_label` 必须是 **QLabel + RichText**（不是 QLineEdit），否则 HTML span 标签原样显示

## 获取引用

```python
getattr(self.window(), "_statusbar_mgr", None)
```
禁止 `import statusbar_manager`（循环导入）。

---

## 相关文档
- [踩坑库](../PITFALLS.md) — QLineEdit HTML 陷阱
- [编码规范](../CONVENTIONS.md) — 状态栏引用/即时刷新规范
