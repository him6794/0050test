# main.py
import os
import requests
import time
from playwright.sync_api import Playwright, sync_playwright

# 從環境變數讀取 Discord Webhook 網址
# 在本機測試時，你可以在終端機設定環境變數，或暫時貼上網址測試(上傳 GitHub 前記得刪掉！)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_message(content):
    """發送訊息到 Discord"""
    if not DISCORD_WEBHOOK_URL:
        print("錯誤: 未設定 DISCORD_WEBHOOK_URL 環境變數，無法發送訊息。")
        # 為了避免在 CI/CD 環境因為這個錯誤而直接中斷，這裡可以選擇 return 或 raise
        # 這裡選擇 return，讓 GitHub Actions 的 Job 能夠完成，但會有錯誤訊息
        return

    data = {
        "content": content,
        "username": "0050 監控機器人" # 你可以隨意改名
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204: # 204 No Content 代表成功發送
            print("訊息已成功發送至 Discord")
        else:
            print(f"發送失敗: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"發送時發生錯誤: {e}")

def run(playwright: Playwright) -> None:
    print("啟動爬蟲...")
    # 啟動瀏覽器 (在 GitHub Actions 上必須是 headless=True)
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        # 1. 前往元大官網
        print("前往元大官網...")
        page.goto("https://www.yuantaetfs.com/product/detail/0050/ratio")
        
        # 2. 處理彈窗 (點擊確定)
        # 使用 try/except 處理彈窗，如果沒出現也不會報錯
        try:
            btn = page.get_by_role("button", name="確定")
            if btn.is_visible(timeout=5000): 
                btn.click()
            else:
                print("Info:彈窗未出現跳過。")
        except Exception:
            print("Info: 彈窗處理失敗或未出現，繼續執行。")

        print("點擊展開按鈕...")
        page.get_by_text("展開").click()
        
        # 4. 等待表格內容出現後，抓取表格文字
        print("抓取表格資料...")
        page.wait_for_selector("div:nth-child(3) > .each_table")
        raw_text = page.locator("div:nth-child(3) > .each_table").all_inner_texts()[0]
        
        print("正在整理報表數據...")
        lines = raw_text.strip().split('\n')
        
        # 準備 Markdown 格式的 Discord 訊息
        message_lines = [
            f"**0050 前十大成分股權重監控**", 
            f"**更新時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "```text" # Discord 的程式碼區塊，用於等寬字體排版
        ]
        # 表頭
        message_lines.append(f"{'代號':<6} {'名稱':<6} {'權重(%)':>8}")
        message_lines.append("-" * 24) # 分隔線
        
        count = 0
        for line in lines:
            parts = line.split()
            # 過濾邏輯：只要有 4 個欄位，且第一個欄位(代碼)是純數字
            if len(parts) == 4 and parts[0].isdigit():
                code, name, _, weight = parts
                # 格式化字串：<6 靠左對齊佔 6 格，>8 靠右對齊佔 8 格
                message_lines.append(f"{code:<6} {name:<6} {weight:>8}")
                count += 1
                if count >= 10: # 只取前 10 名
                    break
        
        message_lines.append("```") # 結束程式碼區塊
        final_msg = "\n".join(message_lines)
        
        # 發送訊息到 Discord
        send_discord_message(final_msg)

    except Exception as e:
        print(f"爬蟲執行發生未預期錯誤: {e}")
        # 如果執行失敗，也發送一個錯誤通知到 Discord
        error_msg = f"**0050 監控機器人執行失敗！**\n錯誤訊息: `{e}`"
        send_discord_message(error_msg)
    finally:
        browser.close()
        print("程式結束。")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
