import os
import json
import requests
import argparse
from datetime import datetime

# 配置区域
# 个人微信推送 (Server酱 方案)
# 如果有多个人要接收，可以用英文逗号分隔填入多个 SendKey，例如 "KEY1,KEY2"
SERVERCHAN_SENDKEYS = [x.strip() for x in os.environ.get("SERVERCHAN_SENDKEY", "SCT355371T08evHGiLp4yR6qFvpgro2qzO").split(",") if x.strip()]

# Steam 游戏配置 (The Bazaar)
GAME_APP_ID = 1617400
STEAM_API_URL = "https://store.steampowered.com/api/appdetails"
STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discount_status.json")

def send_wechat_notification(content):
    """发送推送消息（Server酱 方案）"""
    if not SERVERCHAN_SENDKEYS:
        print(f"[{datetime.now()}] 未配置任何推送 Key，仅输出到控制台：\n{content}")
        return

    for key in SERVERCHAN_SENDKEYS:
        url = f"https://sctapi.ftqq.com/{key}.send"
        payload = {
            "title": "【The Bazaar】折扣监控提醒",
            "desp": content
        }
        try:
            response = requests.post(url, data=payload)
            res_data = response.json()
            if res_data.get("code") == 0 or (res_data.get("data") and res_data["data"].get("error") == "SUCCESS"):
                print(f"[{datetime.now()}] Server酱 微信推送成功 ({key[:10]}...)")
            else:
                print(f"[{datetime.now()}] Server酱 推送失败 ({key[:10]}...): {res_data}")
        except Exception as e:
            print(f"[{datetime.now()}] Server酱 推送出错 ({key[:10]}...): {e}")

def fetch_game_dlcs(app_id):
    """获取游戏及其所有的 DLC 列表"""
    params = {"appids": app_id, "cc": "cn", "l": "zh-cn"}
    try:
        response = requests.get(STEAM_API_URL, params=params)
        data = response.json()
        if str(app_id) in data and data[str(app_id)]["success"]:
            game_data = data[str(app_id)]["data"]
            dlc_ids = game_data.get("dlc", [])
            return game_data.get("name", "The Bazaar"), dlc_ids
    except Exception as e:
        print(f"获取游戏 DLC 列表出错: {e}")
    return "The Bazaar", []

def fetch_dlc_details(dlc_id):
    """获取单个 DLC 的详细价格和打折信息"""
    params = {"appids": dlc_id, "cc": "cn", "l": "zh-cn"}
    try:
        response = requests.get(STEAM_API_URL, params=params)
        data = response.json()
        if str(dlc_id) in data and data[str(dlc_id)]["success"]:
            dlc_data = data[str(dlc_id)]["data"]
            name = dlc_data.get("name")
            price_overview = dlc_data.get("price_overview", {})
            
            initial_price = price_overview.get("initial_formatted", "")
            final_price = price_overview.get("final_formatted", "")
            discount_percent = price_overview.get("discount_percent", 0)
            
            # 如果没有 price_overview，可能是免费或者未定价
            is_free = dlc_data.get("is_free", False)
            if is_free:
                final_price = "免费"
                
            return {
                "id": dlc_id,
                "name": name,
                "discount_percent": discount_percent,
                "initial_price": initial_price or final_price,
                "final_price": final_price,
                "url": f"https://store.steampowered.com/app/{dlc_id}/"
            }
    except Exception as e:
        print(f"获取 DLC [{dlc_id}] 详情出错: {e}")
    return None

def load_previous_status():
    """加载上一次的打折状态记录"""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_current_status(status):
    """保存当前的打折状态记录"""
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存状态文件出错: {e}")

def monitor_discounts(is_daily_report=False):
    game_name, dlc_ids = fetch_game_dlcs(GAME_APP_ID)
    if not dlc_ids:
        print("未找到任何 DLC，请检查网络或 Steam App ID。")
        return

    previous_status = load_previous_status()
    current_status = {}
    
    on_sale_dlcs = []       # 当前正在打折的 DLC 列表
    newly_discounted = []   # 新增打折的 DLC (用于即时推送)
    all_dlcs_info = []      # 所有 DLC 的列表信息 (用于生成日报)

    for dlc_id in dlc_ids:
        info = fetch_dlc_details(dlc_id)
        if info:
            current_status[str(dlc_id)] = info["discount_percent"]
            all_dlcs_info.append(info)
            
            if info["discount_percent"] > 0:
                on_sale_dlcs.append(info)
                # 检查之前是否没打折，或者打折幅度变大了
                prev_discount = previous_status.get(str(dlc_id), 0)
                if info["discount_percent"] > prev_discount:
                    newly_discounted.append(info)

    # 保存最新状态
    save_current_status(current_status)

    # 1. 触发即时折扣提醒（如果有新的打折活动）
    if newly_discounted:
        title = "🚨 **【The Bazaar】DLC 限时打折啦！**\n\n"
        details = ""
        for item in newly_discounted:
            details += (
                f"- **{item['name']}**\n"
                f"  - 折扣：`-{item['discount_percent']}%` (新史低/新活动)\n"
                f"  - 价格：~~{item['initial_price']}~~ ➔ <font color=\"warning\">**{item['final_price']}**</font>\n"
                f"  - 传送门：[点击去Steam购买]({item['url']})\n\n"
            )
        footer = f"> *检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        send_wechat_notification(title + details + footer)
        
    # 2. 触发每日定时播报（在 23:30 时段被触发时）
    elif is_daily_report:
        title = "📅 **【The Bazaar】DLC 打折每日监控日报**\n\n"
        if on_sale_dlcs:
            status_text = "🎉 今天有 **DLC 正在打折** 中：\n\n"
            details = ""
            for item in on_sale_dlcs:
                details += (
                    f"- **{item['name']}**\n"
                    f"  - 折扣：`-{item['discount_percent']}%`\n"
                    f"  - 价格：~~{item['initial_price']}~~ ➔ <font color=\"warning\">**{item['final_price']}**</font>\n"
                    f"  - 传送门：[点击查看]({item['url']})\n\n"
                )
            content = title + status_text + details
        else:
            content = (
                f"{title}"
                f"😴 今天所有的 DLC 均**没有打折活动**。\n\n"
                f"最新价格一览：\n"
            )
            for item in all_dlcs_info:
                content += f"- {item['name']}: **{item['final_price']}**\n"
            content += "\n我们将继续保持每小时监控，有折扣将第一时间群内通知！\n"
            
        footer = f"> *发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        send_wechat_notification(content + footer)
    else:
        print(f"[{datetime.now()}] 监控中：无新打折信息。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Bazaar DLC Discount Monitor")
    parser.add_argument("--daily", action="store_true", help="触发每日定时总结汇报")
    args = parser.parse_args()
    
    monitor_discounts(is_daily_report=args.daily)
