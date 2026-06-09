# 六爻/梅花面板 多列布局规范

## 核心原则：固定列宽容器

**所有多列水平布局必须用 `setFixedWidth` 的 QWidget 包裹每一列，再放入 QHBoxLayout。**

## 为什么

QStackedWidget 会将子 widget 拉伸到自身宽度。如果列直接用 layout 添加（不包容器），layout 内部的 spacing/stretch 会把多余空间分配到列间，导致配置的 `gap_*` 值失效。

## 正确写法

```python
# 左列 — 固定宽度容器
left_total = liushen_w + gap_liushen_to_shiying + shiying_w
self._left_container = QWidget()
self._left_container.setFixedWidth(left_total)
left_vbox = QVBoxLayout(self._left_container)
left_vbox.setContentsMargins(0, 0, 0, 0)
# ... 内部不加 addStretch()

# 右列 — 固定宽度容器
right_total = dongyao_w + gap_dongyao_to_nayin + nayin_w
self._right_container = QWidget()
self._right_container.setFixedWidth(right_total)
right_row = QHBoxLayout(self._right_container)
right_row.setContentsMargins(0, 0, 0, 0)
# ... 内部不加 addStretch()

# 主行
main_row = QHBoxLayout()
main_row.setContentsMargins(0, 0, 0, 0)
main_row.setSpacing(0)
main_row.addWidget(self._left_container)
main_row.addSpacing(gap_marker_to_drawer)   # 可为负值，让标注叠入卦图留白区
main_row.addWidget(self._drawer)
main_row.addSpacing(gap_marker_to_drawer)
main_row.addWidget(self._right_container)
main_row.addStretch()  # 吸收所有多余空间
```

## 错误写法

```python
# ✗ 直接把 layout 加到 main_row — 拉伸时间距会崩
main_row.addLayout(left_vbox)
main_row.addWidget(drawer)

# ✗ 列内有 addStretch() — 会使该列容器膨胀
btn_wrapper.addStretch()
ls_row.addStretch()
```

## 宽度变更时

内容变化导致列宽需要更新时（如纳音文字变了），调用 `_update_container_widths()` 刷新容器 `setFixedWidth`。

## 垂直方向

- marker 通过 `setFixedHeight(6 * line_h)` 限制高度
- nayin badge 通过 `badge_h = min(..., self._line_h)` 防止相邻行重叠
- 负值 `gap_marker_to_drawer` 利用 drawer 内部 15px 留白实现标注叠入效果
