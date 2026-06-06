#!/bin/bash
# ──────────────────────────────────────────────────────
# 易经数据库工具集入口（macOS 双击运行）
# ──────────────────────────────────────────────────────
# 选项1 → yijing_manager.py          数据库管理（编辑/备份/恢复/批量字段）
# 选项2 → sync_structure.py          格式刷（以01_乾.jsonc为模板同步64卦结构）
# 选项3 → import_home_fields.py      自动填充 nishi.home（上卦→成员, 下卦→方位）
# 选项4 → import_nishi_diagram.py    自动填充倪师卦图解
# 选项5 → lock_manager.py            字段锁管理
# 选项6 → chmod 文件夹权限管理        只读/可写切换
# ──────────────────────────────────────────────────────
cd "$(dirname "$0")"

while true; do
    clear
    echo "╔══════════════════════════════════════╗"
    echo "║       易经数据库工具集               ║"
    echo "╠══════════════════════════════════════╣"
    echo "║  1. 数据库管理（编辑/备份/恢复）     ║"
    echo "║  2. 格式刷（同步结构+刷新格式）      ║"
    echo "║  3. 自动填充 home 字段（上下卦映射） ║"
    echo "║  4. 自动填充倪师卦图解               ║"
    echo "║  5. 🔒字段锁管理                     ║"
echo "║  6. 📁文件夹权限（只读/可写）        ║"
    echo "║  q. 退出                             ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    read -p "请选择 (1/2/3/4/5/6/q): " choice
    case $choice in
        1) echo "" && echo "→ 启动 yijing_manager.py 数据库管理工具..." && echo "" && python3 yijing_manager.py ;;
        2)
            clear
            echo "╔══════════════════════════════════════════════╗"
            echo "║           格式刷 — 使用说明                  ║"
            echo "╠══════════════════════════════════════════════╣"
            echo "║                                              ║"
            echo "║  模板文件：01_乾.jsonc                       ║"
            echo "║  作用范围：其余 63 卦 + lock.jsonc           ║"
            echo "║                                              ║"
            echo "║  执行操作：                                  ║"
            echo "║  ◇ 结构同步 — 补齐模板有、目标缺的字段       ║"
            echo "║  ◇ 字段清理 — 删除目标多余的空字段           ║"
            echo "║  ◇ 字段排序 — 按模板顺序重排                 ║"
            echo "║  ◇ 格式刷新 — 对齐缩进、注释、换行           ║"
            echo "║  ◇ 锁同步   — 更新 lock.jsonc 保留已有锁值   ║"
            echo "║                                              ║"
            echo "║  安全机制：                                  ║"
            echo "║  ◇ 运行前自动备份 → content.bkp.zip          ║"
            echo "║  ◇ 有内容的多余字段 → 拦截并提示迁移         ║"
            echo "║  ◇ 不检查锁，结构同步优先级最高              ║"
            echo "║  ◇ 可反复运行，已同步文件仅刷新格式          ║"
            echo "║                                              ║"
            echo "╚══════════════════════════════════════════════╝"
            echo ""
            read -p "按回车执行格式刷，输入 q/0 返回主菜单: " confirm
            if [ "$confirm" = "q" ] || [ "$confirm" = "Q" ] || [ "$confirm" = "0" ]; then
                continue
            fi
            echo ""
            python3 sync_structure.py
            ;;
        3)
            clear
            echo "╔══════════════════════════════════════════════╗"
            echo "║       自动填充 home 字段（上下卦映射）       ║"
            echo "╠══════════════════════════════════════════════╣"
            echo "║                                              ║"
            echo "║  规则：上卦(upper) → 家庭成员                ║"
            echo "║        下卦(lower) → 方位                    ║"
            echo "║                                              ║"
            echo "║  映射：                                      ║"
            echo "║  乾=父亲/西北  坤=母亲/西南  震=长男/东       ║"
            echo "║  巽=长女/东南  坎=中男/北    离=中女/南       ║"
            echo "║  艮=少男/东北  兑=少女/西                    ║"
            echo "║                                              ║"
            echo "║  目标字段：nishi.home.member                  ║"
            echo "║            nishi.home.direction               ║"
            echo "║  绕开锁机制，直接写入                        ║"
            echo "║                                              ║"
            echo "╚══════════════════════════════════════════════╝"
            echo ""
            read -p "按回车执行，输入 q/0 返回主菜单: " confirm
            if [ "$confirm" = "q" ] || [ "$confirm" = "Q" ] || [ "$confirm" = "0" ]; then
                continue
            fi
            echo ""
            python3 import_home_fields.py
            echo ""
            read -p "按回车返回主菜单..." dummy
            ;;
        4)
            clear
            echo "╔══════════════════════════════════════════════╗"
            echo "║        自动填充倪师卦图解                    ║"
            echo "╠══════════════════════════════════════════════╣"
            echo "║                                              ║"
            echo "║  数据源：diagram/倪师卦像图解.md             ║"
            echo "║  目标字段：nishi.diagram.description（数组）  ║"
            echo "║                                              ║"
            echo "║  执行操作：                                  ║"
            echo "║  ◇ 解析 MD 中 64 卦的卦圖象解条目            ║"
            echo "║  ◇ 覆盖写入 description（替换原有内容）      ║"
            echo "║  ◇ 自动备份 → content.bkp.zip                ║"
            echo "║                                              ║"
            echo "║  绕开锁机制，直接写入                        ║"
            echo "║                                              ║"
            echo "╚══════════════════════════════════════════════╝"
            echo ""
            read -p "按回车执行，输入 q/0 返回主菜单: " confirm
            if [ "$confirm" = "q" ] || [ "$confirm" = "Q" ] || [ "$confirm" = "0" ]; then
                continue
            fi
            echo ""
            python3 import_nishi_diagram.py
            echo ""
            read -p "按回车返回主菜单..." dummy
            ;;
        5) echo "" && echo "→ 启动 lock_manager.py 字段锁管理..." && echo "" && python3 lock_manager.py ;;
        6)
            PARENT_DIR="$(cd .. && pwd)"

            # 收集文件夹列表
            FOLDERS=()
            FOLDER_NAMES=()
            for d in "$PARENT_DIR"/*/; do
                name=$(basename "$d")
                case "$name" in
                    content|diagram|MgrScript|MgrScript_bak)
                        FOLDERS+=("$d")
                        FOLDER_NAMES+=("$name")
                        ;;
                esac
            done

            if [ ${#FOLDERS[@]} -eq 0 ]; then
                echo "❌ 未找到可管理的文件夹"
                echo ""
                read -p "按回车返回主菜单..." dummy
                continue
            fi

            # 内层循环：操作完成后回到选择界面
            while true; do
                clear
                echo "╔══════════════════════════════════════════════╗"
                echo "║       文件夹权限管理（只读/可写）             ║"
                echo "╠══════════════════════════════════════════════╣"
                echo "║                                              ║"
                echo "║  当前目录: ../ (src/data/yijing)                 ║"
                echo "║                                              ║"
                echo "║  只读(a-w) → 防止误改    可写(u+w) → 正常编辑 ║"
                echo "║  支持多选：1,2 或 1 2 或 1 3-5               ║"
                echo "║                                              ║"
                echo "╚══════════════════════════════════════════════╝"
                echo ""

                echo "  可管理的文件夹："
                echo ""
                for i in "${!FOLDERS[@]}"; do
                    d="${FOLDERS[$i]}"
                    name="${FOLDER_NAMES[$i]}"
                    if [ ! -w "$d" ]; then
                        status="🔒 只读"
                    else
                        status="✅ 可写"
                    fi
                    printf "  %d. %-20s %s\n" $((i+1)) "$name" "$status"
                done
                echo "  *  所有文件夹"
                echo "  0  返回主菜单"
                echo ""

                read -p "请选择要操作的文件夹 (1-${#FOLDERS[@]}/*/0/q, 支持多选): " folder_choice

                if [ "$folder_choice" = "0" ] || [ "$folder_choice" = "q" ] || [ "$folder_choice" = "Q" ] || [ -z "$folder_choice" ]; then
                    break
                fi

                # "*" 选择所有
                if [ "$folder_choice" = "*" ]; then
                    echo ""
                    has_readonly=false
                    for d in "${FOLDERS[@]}"; do
                        if [ ! -w "$d" ]; then
                            has_readonly=true
                            break
                        fi
                    done

                    if $has_readonly; then
                        echo "⚠️  检测到有只读文件夹，将恢复为可写状态。"
                        read -p "确认恢复所有文件夹为可写？(y/1 确认，其他取消): " confirm
                        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || [ "$confirm" = "1" ]; then
                            for d in "${FOLDERS[@]}"; do
                                chmod -R u+w "$d" 2>/dev/null
                                echo "  ✅ $(basename "$d") → 已恢复可写"
                            done
                        else
                            echo "  已取消"
                        fi
                    else
                        echo "  所有文件夹均为可写，设置为只读..."
                        for d in "${FOLDERS[@]}"; do
                            chmod -R a-w "$d" 2>/dev/null
                            echo "  🔒 $(basename "$d") → 已设为只读"
                        done
                    fi
                    echo ""
                    read -p "按回车继续..." dummy
                    continue
                fi

                # 解析选择：替换逗号为空格，展开范围 3-5 → 3 4 5
                N=$((${#FOLDERS[@]}))
                # 将逗号替换为空格
                normalized=$(echo "$folder_choice" | tr ',' ' ')
                # 展开范围
                expanded=""
                for token in $normalized; do
                    if echo "$token" | grep -q '^[0-9]\+-[0-9]\+$'; then
                        start=${token%-*}
                        end=${token#*-}
                        if [ "$start" -le "$end" ] 2>/dev/null; then
                            for j in $(seq "$start" "$end"); do
                                expanded="$expanded $j"
                            done
                        else
                            expanded="$expanded $token"
                        fi
                    else
                        expanded="$expanded $token"
                    fi
                done

                # 验证并收集要操作的文件夹索引
                selected_indices=()
                invalid_tokens=""
                for token in $expanded; do
                    if [ "$token" -ge 1 ] 2>/dev/null && [ "$token" -le "$N" ] 2>/dev/null; then
                        selected_indices+=($((token - 1)))
                    else
                        invalid_tokens="$invalid_tokens $token"
                    fi
                done

                if [ ${#selected_indices[@]} -eq 0 ]; then
                    echo ""
                    echo "❌ 未选中有效文件夹"
                    sleep 1
                    continue
                fi

                if [ -n "$invalid_tokens" ]; then
                    echo ""
                    echo "⚠️  忽略无效输入:$invalid_tokens"
                fi

                echo ""

                # 检查所选文件夹的只读情况
                readonly_selected=()
                writable_selected=()
                for idx in "${selected_indices[@]}"; do
                    d="${FOLDERS[$idx]}"
                    if [ ! -w "$d" ]; then
                        readonly_selected+=("$idx")
                    else
                        writable_selected+=("$idx")
                    fi
                done

                # 只读文件夹 → 逐个确认恢复可写
                if [ ${#readonly_selected[@]} -gt 0 ]; then
                    echo "  ── 只读 → 恢复可写 ──"
                    for idx in "${readonly_selected[@]}"; do
                        name="${FOLDER_NAMES[$idx]}"
                        read -p "  ⚠️  「${name}」为只读，确认恢复可写？(y/1 确认，其他跳过): " confirm
                        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || [ "$confirm" = "1" ]; then
                            chmod -R u+w "${FOLDERS[$idx]}" 2>/dev/null
                            echo "    ✅ ${name} → 已恢复可写"
                        else
                            echo "    ↪  跳过 ${name}"
                        fi
                    done
                fi

                # 可写文件夹 → 直接设为只读（无需确认）
                if [ ${#writable_selected[@]} -gt 0 ]; then
                    echo "  ── 可写 → 设为只读 ──"
                    for idx in "${writable_selected[@]}"; do
                        name="${FOLDER_NAMES[$idx]}"
                        chmod -R a-w "${FOLDERS[$idx]}" 2>/dev/null
                        echo "  🔒 ${name} → 已设为只读"
                    done
                fi

                echo ""
                read -p "按回车继续..." dummy
            done
            ;;
        q|Q) echo "再见" && exit 0 ;;
        *) echo "无效选择" && sleep 1 ;;
    esac
done
