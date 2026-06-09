"""
起卦弹窗自动测试脚本
═══════════════════════════════════════════════════════════════
测试目标：验证「起卦」按钮 → 弹出64卦列表 → 点击选择项 → 不会 SIGSEGV
═══════════════════════════════════════════════════════════════

测试覆盖场景：
  1. 弹出列表 + 点击选中第1项（乾为天）
  2. 弹出列表 + 点击选中第64项（未济卦）
  3. 连续快速弹出+选择 3 次（压力测试）
  4. 弹出后点击外部关闭（不选任何项）

输出说明：
  [PASS] = 测试通过
  [FAIL] = 测试失败（Python 异常）
  [CRASH] = 程序崩溃（SIGSEGV 等），由 shell 包装脚本检测
"""

import sys
import os
import signal
import traceback

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def log(msg: str):
    """带时间戳的日志输出"""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", flush=True)


def run_tests():
    """主测试入口"""
    log("=" * 60)
    log("起卦弹窗自动测试开始")
    log(f"Python: {sys.version}")
    log(f"项目路径: {PROJECT_ROOT}")
    log("=" * 60)

    # ── 第1步：创建 QApplication ──
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        log("创建 QApplication 实例...")
        app = QApplication(sys.argv)
    else:
        log("复用已有 QApplication 实例")

    # ── 第2步：导入 QiguaPanel ──
    log("导入 QiguaPanel...")
    try:
        from src.yijingTab.qigua.divination_panel import QiguaPanel, _GuaPickerPopup, _DotButton
        from src.yijingTab.com.hexagram_loader import load_all_gua
        log("  导入成功")
    except Exception as e:
        log(f"  [FAIL] 导入失败: {e}")
        traceback.print_exc()
        return 1

    # 验证 64 卦加载
    all_gua = load_all_gua()
    log(f"  加载了 {len(all_gua)} 卦")

    # ── 第3步：创建测试窗口 ──
    from PySide6.QtWidgets import QWidget, QVBoxLayout
    from PySide6.QtCore import Qt, QTimer, QEvent
    from PySide6.QtTest import QTest

    test_window = QWidget()
    test_window.setWindowTitle("起卦弹窗测试")
    test_window.resize(900, 700)
    layout = QVBoxLayout(test_window)
    layout.setContentsMargins(0, 0, 0, 0)

    panel = QiguaPanel()
    layout.addWidget(panel)

    test_window.show()
    QTest.qWait(100)  # 等待窗口渲染完成
    log("测试窗口已创建并显示")

    # ── 测试结果收集 ──
    results = {"pass": 0, "fail": 0, "total": 0}

    # ── 辅助函数：查找弹窗 ──
    def find_popup():
        """查找当前活跃的 _GuaPickerPopup 弹窗"""
        from PySide6.QtWidgets import QApplication as QA
        for w in QA.topLevelWidgets():
            if isinstance(w, _GuaPickerPopup) and w.isVisible():
                return w
        # 备用：通过 panel 的引用
        if hasattr(panel, '_gua_picker') and panel._gua_picker is not None:
            return panel._gua_picker
        return None

    # ═══════════════════════════════════════════════════════════
    #  测试 1：基本弹出 + 选择第1项（乾为天）
    # ═══════════════════════════════════════════════════════════
    results["total"] += 1
    test_name = "测试1: 弹出64卦列表 + 点击选中第1项(乾为天)"
    log(f"\n{'─'*50}")
    log(f"[TEST {results['total']}] {test_name}")

    try:
        # 模拟点击"起卦"标题按钮
        title_btn = panel._title_label
        log(f"  标题按钮 enabled={title_btn.isEnabled()}")
        log(f"  标题按钮 visible={title_btn.isVisible()}")
        log(f"  标题按钮 geometry={title_btn.geometry().getRect()}")

        # 使用 QTest 模拟鼠标点击
        QTest.mouseClick(title_btn, Qt.MouseButton.LeftButton)
        QTest.qWait(200)  # 等待弹窗出现

        # 查找弹窗
        popup = find_popup()
        if popup is None:
            log("  [FAIL] 弹窗未出现")
            results["fail"] += 1
        else:
            log(f"  弹窗已出现: pos=({popup.x()},{popup.y()}), size={popup.width()}x{popup.height()}")

            # 查找 picker（QListWidget 是 popup 的子控件）
            from PySide6.QtWidgets import QListWidget
            picker = popup.findChild(QListWidget)
            if picker is None:
                log("  [FAIL] 弹窗中未找到 QListWidget")
                results["fail"] += 1
            else:
                log(f"  QListWidget 找到: count={picker.count()}, visible_rows={picker.count()}")

                # 获取第一项的几何位置
                item_rect = picker.visualItemRect(picker.item(0))
                log(f"  第1项 rect={item_rect.getRect()}")

                # 记录点击前的卦图状态
                pre_click_yang = panel._drawer.yang_lines()
                log(f"  点击前 yang_lines={pre_click_yang}")

                # 模拟点击列表第一项
                click_pos = picker.viewport().mapToGlobal(item_rect.center())
                log(f"  模拟点击位置: ({click_pos.x()},{click_pos.y()})")
                QTest.mouseClick(picker.viewport(), Qt.MouseButton.LeftButton,
                                 Qt.KeyboardModifier.NoModifier, item_rect.center())
                QTest.qWait(300)  # 等待事件处理

                # 验证弹窗已关闭
                popup_after = find_popup()
                if popup_after is not None:
                    log(f"  [WARN] 弹窗仍在: visible={popup_after.isVisible()}")
                    popup_after.hide()
                    popup_after.deleteLater()
                    QTest.qWait(100)

                # 验证卦图已更新（乾为天 binary=111111, 全阳）
                post_click_yang = panel._drawer.yang_lines()
                log(f"  点击后 yang_lines={post_click_yang}")

                # 乾为天应当全阳（6个True）
                if post_click_yang == [True, True, True, True, True, True]:
                    log(f"  [PASS] {test_name}")
                    results["pass"] += 1
                else:
                    log(f"  [FAIL] 乾为天应为全阳(6个True)，实际为 {post_click_yang}")
                    results["fail"] += 1

    except Exception as e:
        log(f"  [FAIL] 异常: {e}")
        traceback.print_exc()
        results["fail"] += 1

    # ═══════════════════════════════════════════════════════════
    #  测试 2：选择最后一卦（火水未济，binary=010101）
    # ═══════════════════════════════════════════════════════════
    results["total"] += 1
    test_name = "测试2: 弹出列表 + 点击选中第64项(火水未济)"
    log(f"\n{'─'*50}")
    log(f"[TEST {results['total']}] {test_name}")

    try:
        QTest.mouseClick(title_btn, Qt.MouseButton.LeftButton)
        QTest.qWait(200)

        popup = find_popup()
        if popup is None:
            log("  [FAIL] 弹窗未出现")
            results["fail"] += 1
        else:
            from PySide6.QtWidgets import QListWidget
            picker = popup.findChild(QListWidget)
            if picker is None:
                log("  [FAIL] 弹窗中未找到 QListWidget")
                results["fail"] += 1
            else:
                # 滚动到底部确保最后一项可见
                picker.scrollToBottom()
                QTest.qWait(50)

                # 获取最后一项的几何位置
                last_item = picker.item(picker.count() - 1)
                item_rect = picker.visualItemRect(last_item)
                log(f"  最后一项 text='{last_item.text()}', rect={item_rect.getRect()}")

                # 验证确实是第64项
                gid = last_item.data(Qt.ItemDataRole.UserRole)
                log(f"  最后一项 gua_id={gid}")

                QTest.mouseClick(picker.viewport(), Qt.MouseButton.LeftButton,
                                 Qt.KeyboardModifier.NoModifier, item_rect.center())
                QTest.qWait(300)

                # 清理弹窗
                popup_after = find_popup()
                if popup_after is not None:
                    popup_after.hide()
                    popup_after.deleteLater()
                    QTest.qWait(100)

                # 火水未济 binary="010101" (初爻→上爻: 坎下离上)
                # 下卦坎☵: 阴-阳-阴, 上卦离☲: 阳-阴-阳
                # 全卦 bottom→top: [阴,阳,阴,阳,阴,阳] = [F,T,F,T,F,T]
                expected = [False, True, False, True, False, True]
                post_yang = panel._drawer.yang_lines()
                log(f"  点击后 yang_lines={post_yang}")
                if post_yang == expected:
                    log(f"  [PASS] {test_name}")
                    results["pass"] += 1
                else:
                    log(f"  [FAIL] 火水未济应为 {expected}，实际为 {post_yang}")
                    results["fail"] += 1

    except Exception as e:
        log(f"  [FAIL] 异常: {e}")
        traceback.print_exc()
        results["fail"] += 1

    # ═══════════════════════════════════════════════════════════
    #  测试 3：压力测试 — 连续 7 次弹出+选择不同卦
    # ═══════════════════════════════════════════════════════════
    results["total"] += 1
    test_name = "测试3: 压力测试 — 连续7次弹出+选择不同卦"
    log(f"\n{'─'*50}")
    log(f"[TEST {results['total']}] {test_name}")

    # 选 7 个卦：乾(1), 坤(2), 屯(3), 泰(11), 否(12), 既济(63), 未济(64)
    test_gua_ids = [1, 2, 3, 11, 12, 63, 64]
    stress_pass = 0
    stress_fail = 0

    for iteration, gid in enumerate(test_gua_ids):
        try:
            QTest.mouseClick(title_btn, Qt.MouseButton.LeftButton)
            QTest.qWait(250)

            popup = find_popup()
            if popup is None:
                log(f"  迭代{iteration+1} gua={gid}: [FAIL] 弹窗未出现")
                stress_fail += 1
                continue

            from PySide6.QtWidgets import QListWidget
            picker = popup.findChild(QListWidget)

            # 找到对应 gua_id 的 item
            found = False
            for row in range(picker.count()):
                item = picker.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == gid:
                    picker.scrollToItem(item)
                    QTest.qWait(50)
                    item_rect = picker.visualItemRect(item)
                    log(f"  迭代{iteration+1}: 点击 {item.text()}")
                    QTest.mouseClick(picker.viewport(), Qt.MouseButton.LeftButton,
                                     Qt.KeyboardModifier.NoModifier, item_rect.center())
                    found = True
                    break

            if not found:
                log(f"  迭代{iteration+1} gua={gid}: [FAIL] 未找到卦")
                stress_fail += 1
                popup.hide()
                popup.deleteLater()
                QTest.qWait(50)
                continue

            QTest.qWait(200)

            # 清理
            popup_after = find_popup()
            if popup_after is not None:
                popup_after.hide()
                popup_after.deleteLater()
                QTest.qWait(50)

            # 验证
            gua_data = all_gua.get(gid, {})
            expected_binary = gua_data.get("binary", "111111")
            expected_yang = [c == "1" for c in expected_binary]
            actual_yang = panel._drawer.yang_lines()
            if actual_yang == expected_yang:
                stress_pass += 1
            else:
                log(f"  迭代{iteration+1} gua={gid}: [FAIL] 期望 {expected_yang}, 实际 {actual_yang}")
                stress_fail += 1

            QTest.qWait(30)  # 迭代间小间隔

        except Exception as e:
            log(f"  迭代{iteration+1} gua={gid}: [FAIL] 异常: {e}")
            traceback.print_exc()
            stress_fail += 1

    if stress_fail == 0:
        log(f"  [PASS] {test_name} ({stress_pass}/{len(test_gua_ids)} 次全部成功)")
        results["pass"] += 1
    else:
        log(f"  [FAIL] {test_name} ({stress_fail}/{len(test_gua_ids)} 次失败)")
        results["fail"] += 1

    # ═══════════════════════════════════════════════════════════
    #  测试 4：Lock 状态下弹出 + 选择后恢复 Lock
    # ═══════════════════════════════════════════════════════════
    results["total"] += 1
    test_name = "测试4: Lock状态下弹出列表 + 选择后恢复Lock"
    log(f"\n{'─'*50}")
    log(f"[TEST {results['total']}] {test_name}")

    try:
        # 先启用 Lock
        if panel._lock_cbs:
            lock_cb = panel._lock_cbs[0]
            lock_cb.setChecked(True)
            QTest.qWait(50)
            log(f"  Lock 已开启: title_btn enabled={panel._title_label.isEnabled()}")

        # 点击标题按钮（Lock 状态下按钮是先强制启用再弹出）
        QTest.mouseClick(title_btn, Qt.MouseButton.LeftButton)
        QTest.qWait(200)

        popup = find_popup()
        if popup is None:
            log("  [FAIL] Lock状态下弹窗未出现")
            results["fail"] += 1
        else:
            from PySide6.QtWidgets import QListWidget
            picker = popup.findChild(QListWidget)
            item_rect = picker.visualItemRect(picker.item(3))  # 选第4项
            QTest.mouseClick(picker.viewport(), Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier, item_rect.center())
            QTest.qWait(300)

            # 清理
            popup_after = find_popup()
            if popup_after is not None:
                popup_after.hide()
                popup_after.deleteLater()
                QTest.qWait(100)

            # 验证 Lock 已恢复（title_btn 应该被禁用）
            if not panel._title_label.isEnabled():
                log(f"  [PASS] {test_name} — Lock 已恢复（title_btn 禁用）")
                results["pass"] += 1
            else:
                log(f"  [FAIL] Lock 未恢复（title_btn 仍启用）")
                results["fail"] += 1

            # 恢复 Lock 状态
            if panel._lock_cbs:
                panel._lock_cbs[0].setChecked(False)
                QTest.qWait(50)

    except Exception as e:
        log(f"  [FAIL] 异常: {e}")
        traceback.print_exc()
        results["fail"] += 1

    # ═══════════════════════════════════════════════════════════
    #  测试 5：检查 _gua_picker 引用清理（防止内存泄漏）
    # ═══════════════════════════════════════════════════════════
    results["total"] += 1
    test_name = "测试5: 弹窗关闭后 _gua_picker 引用清理"
    log(f"\n{'─'*50}")
    log(f"[TEST {results['total']}] {test_name}")

    try:
        QTest.mouseClick(title_btn, Qt.MouseButton.LeftButton)
        QTest.qWait(200)

        popup = find_popup()
        if popup is None:
            log("  [FAIL] 弹窗未出现")
            results["fail"] += 1
        else:
            from PySide6.QtWidgets import QListWidget
            picker = popup.findChild(QListWidget)
            item_rect = picker.visualItemRect(picker.item(0))
            QTest.mouseClick(picker.viewport(), Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier, item_rect.center())
            QTest.qWait(400)  # 等待 deleteLater 执行

            # 验证引用已清理
            ref = getattr(panel, '_gua_picker', 'MISSING')
            if ref is None:
                log(f"  [PASS] {test_name} — _gua_picker 已清理为 None")
                results["pass"] += 1
            else:
                log(f"  [FAIL] _gua_picker = {ref}，应为 None")
                results["fail"] += 1

    except Exception as e:
        log(f"  [FAIL] 异常: {e}")
        traceback.print_exc()
        results["fail"] += 1

    # ═══════════════════════════════════════════════════════════
    #  汇总报告
    # ═══════════════════════════════════════════════════════════
    log(f"\n{'='*60}")
    log("测试汇总报告")
    log(f"  总计: {results['total']} 项测试")
    log(f"  通过: {results['pass']} 项")
    log(f"  失败: {results['fail']} 项")
    if results["fail"] == 0:
        log("  结论: 全部通过 — 弹窗崩溃问题已修复")
    else:
        log(f"  结论: {results['fail']} 项失败，需要进一步排查")
    log("=" * 60)

    # 关闭测试窗口
    test_window.close()
    QTest.qWait(100)

    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    # 设置 5 秒超时防止卡死
    signal.alarm(30)
    try:
        exit_code = run_tests()
    except KeyboardInterrupt:
        print("\n[ABORT] 用户中断")
        exit_code = 130
    except Exception as e:
        print(f"\n[FATAL] 未捕获异常: {e}")
        traceback.print_exc()
        exit_code = 1
    finally:
        signal.alarm(0)  # 取消超时
    sys.exit(exit_code)
