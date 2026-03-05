#!/usr/bin/env python3
"""
Lambda Cloud GPU Instance Monitor
===================================
监控 Lambda Cloud 的 GPU 实例可用性，当有空闲实例时通过终端输出和系统通知提醒。

使用方法：
  1. 获取 API Key: 登录 https://cloud.lambdalabs.com → API Keys → 生成一个 key
  2. 运行: python3 lambda_monitor.py
  3. 输入你的 API Key（或设置环境变量 LAMBDA_API_KEY）
  4. 按 Ctrl+C 停止监控

依赖安装：
  pip install requests
"""

import requests
import time
import os
import sys
import platform
import subprocess
from datetime import datetime

# ======================== 配置 ========================
API_URL = "https://cloud.lambdalabs.com/api/v1/instance-types"
CHECK_INTERVAL = 60          # 检查间隔（秒）
NOTIFY_COOLDOWN = 300        # 同一实例类型通知冷却时间（秒），避免重复通知
# =====================================================

# ANSI 颜色
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


def get_api_key():
    """获取 API Key"""
    key = os.environ.get("LAMBDA_API_KEY", "").strip()
    if key:
        print(f"{C.GREEN}✓ 已从环境变量 LAMBDA_API_KEY 读取 API Key{C.RESET}")
        return key
    key = input(f"{C.CYAN}请输入你的 Lambda Cloud API Key: {C.RESET}").strip()
    if not key:
        print(f"{C.RED}错误: API Key 不能为空{C.RESET}")
        sys.exit(1)
    return key


def check_availability(api_key):
    """调用 Lambda API 检查实例可用性"""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(API_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    available = {}
    all_types = {}

    for name, info in data.get("data", {}).items():
        instance = info.get("instance_type", {})
        desc = instance.get("description", name)
        price = instance.get("price_cents_per_hour", 0) / 100
        specs = instance.get("specs", {})
        gpu_count = specs.get("gpus", 0)
        ram = specs.get("ram_gib", 0)
        vcpus = specs.get("vcpus", 0)
        storage = specs.get("storage_gib", 0)

        regions = info.get("regions_with_capacity_available", [])
        region_names = [r.get("name", r.get("description", "unknown")) for r in regions]

        type_info = {
            "name": name,
            "description": desc,
            "price": price,
            "gpu_count": gpu_count,
            "ram_gib": ram,
            "vcpus": vcpus,
            "storage_gib": storage,
            "regions": region_names,
        }
        all_types[name] = type_info
        if regions:
            available[name] = type_info

    return available, all_types


def system_notify(title, message):
    """发送系统通知"""
    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{message}" with title "{title}" sound name "Glass"'],
                capture_output=True, timeout=5
            )
        elif system == "Linux":
            subprocess.run(
                ["notify-send", "-u", "critical", title, message],
                capture_output=True, timeout=5
            )
        elif system == "Windows":
            # PowerShell toast notification
            ps_cmd = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{title}'))
            $xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{message}'))
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Lambda Monitor').Show($toast)
            """
            subprocess.run(["powershell", "-Command", ps_cmd],
                           capture_output=True, timeout=5)
    except Exception:
        pass  # 通知失败不影响主流程

    # 终端响铃
    print("\a", end="", flush=True)


def format_instance(info, is_new=False):
    """格式化单个实例信息"""
    tag = f"{C.YELLOW}🆕 NEW!{C.RESET} " if is_new else "       "
    return (
        f"  {tag}{C.BOLD}{info['description']}{C.RESET}\n"
        f"          💰 ${info['price']:.2f}/hr  |  "
        f"🖥 {info['gpu_count']} GPU  |  "
        f"💾 {info['ram_gib']} GB RAM  |  "
        f"📦 {info['storage_gib']} GB Storage\n"
        f"          🌍 Regions: {', '.join(info['regions'])}"
    )


def print_banner():
    """打印启动横幅"""
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════╗
║       Lambda Cloud GPU Instance Monitor          ║
║                                                  ║
║  监控所有 GPU 实例类型 · 每 {CHECK_INTERVAL} 秒检查一次        ║
╚══════════════════════════════════════════════════╝{C.RESET}
""")


def main():
    print_banner()
    api_key = get_api_key()

    # 验证 API Key
    print(f"\n{C.CYAN}验证 API Key...{C.RESET}", end=" ", flush=True)
    try:
        available, all_types = check_availability(api_key)
        print(f"{C.GREEN}✓ 成功！发现 {len(all_types)} 种实例类型{C.RESET}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"{C.RED}✗ API Key 无效，请检查后重试{C.RESET}")
        else:
            print(f"{C.RED}✗ HTTP 错误: {e}{C.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{C.RED}✗ 连接失败: {e}{C.RESET}")
        sys.exit(1)

    print(f"\n{C.GREEN}开始监控... 按 Ctrl+C 停止{C.RESET}\n")
    print(f"{'─' * 60}")

    prev_available = set()
    notified = {}  # {instance_name: last_notify_timestamp}
    check_count = 0

    while True:
        try:
            check_count += 1
            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S")

            available, _ = check_availability(api_key)

            if available:
                current_set = set(available.keys())
                new_instances = current_set - prev_available

                print(f"\n{C.GREEN}{C.BOLD}[{timestamp}] 🟢 #{check_count} "
                      f"发现 {len(available)} 种可用实例！{C.RESET}")

                for name, info in sorted(available.items(),
                                         key=lambda x: x[1]["price"]):
                    is_new = name in new_instances
                    print(format_instance(info, is_new))

                # 对新出现的实例发送通知（带冷却）
                for name in new_instances:
                    last = notified.get(name, 0)
                    if time.time() - last > NOTIFY_COOLDOWN:
                        desc = available[name]["description"]
                        price = available[name]["price"]
                        regions = ", ".join(available[name]["regions"])
                        system_notify(
                            "🟢 Lambda GPU 可用!",
                            f"{desc} - ${price:.2f}/hr ({regions})"
                        )
                        notified[name] = time.time()

                prev_available = current_set
            else:
                print(f"  {C.RED}[{timestamp}] 🔴 #{check_count} "
                      f"暂无可用实例{C.RESET}", end="\r")
                sys.stdout.flush()
                prev_available = set()

        except requests.exceptions.RequestException as e:
            print(f"  {C.YELLOW}[{timestamp}] ⚠ 网络错误: {e}{C.RESET}")
        except Exception as e:
            print(f"  {C.RED}[{timestamp}] ❌ 异常: {e}{C.RESET}")

        try:
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            break

    print(f"\n\n{C.CYAN}监控已停止。共检查 {check_count} 次。{C.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.CYAN}已退出。{C.RESET}")
