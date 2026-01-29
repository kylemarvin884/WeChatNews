import os
import time
from datetime import datetime, timedelta, timezone
import requests
import feedparser


def get_recent_stories():
    """
    从 Hacker News RSS 获取过去 24 小时的故事标题。
    你可以替换这个函数来抓取你想要的科技资讯源。
    """
    print("Fetching stories from Hacker News...")
    rss_url = "https://news.ycombinator.com/rss"
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"Error fetching or parsing RSS feed: {e}")
        return []

    if not feed.entries:
        print("No entries found in the feed.")
        return []

    # 获取 24 小时前的时间戳 (UTC)
    utc_now = datetime.now(timezone.utc)
    twenty_four_hours_ago = utc_now - timedelta(hours=24)

    recent_titles = []
    for entry in feed.entries:
        # 尝试解析 entry 的发布时间
        published_parsed = entry.get('published_parsed')
        if published_parsed:
            entry_time = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        else:
             # 如果没有明确的发布时间，可以选择跳过或视为最新
             # 这里为了安全起见，假设没有时间的就是旧的，跳过
             continue

        # 检查是否在过去 24 小时内
        if entry_time >= twenty_four_hours_ago:
            title = entry.title
            link = entry.link
            # 限制标题长度，避免消息过长
            truncated_title = f"{title[:100]}..." if len(title) > 100 else title
            recent_titles.append(f"- [{truncated_title}]({link})")
        elif entry_time < twenty_four_hours_ago:
            # 因为 RSS 通常是按时间倒序排列的，一旦遇到超过 24 小时的就可以停止了
            break

    print(f"Found {len(recent_titles)} recent stories.")
    return recent_titles


def send_to_wechat(message):
    """
    通过 Server酱 (ServerChan) 推送消息到微信
    """
    # 打印 SendKey 的前几位用于调试，不泄露完整密钥
    sendkey = os.getenv("SERVER_CHAN_SENDKEY")
    if not sendkey:
        print("ERROR: SERVER_CHAN_SENDKEY environment variable not found!")
        print("Please check your GitHub Secrets configuration.")
        return False

    # --- Debugging Info Start ---
    print("--- DEBUGGING INFO START ---")
    print(f"Retrieved SendKey (first 5 chars): {sendkey[:5]}...")
    print("--- DEBUGGING INFO END ---")
    # --- Debugging Info End ---

    if not message.strip():
         message = "今日暂无更新的科技资讯。"

    # 准备发送的数据
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    title = f"【每日科技资讯】{datetime.now().strftime('%Y-%m-%d')}"
    
    # Server酱 v3 推荐使用 title 和 desp
    data = {
        "title": title,
        "desp": message # 支持 Markdown 格式
    }

    # --- Debugging Info Start ---
    print("--- DEBUGGING INFO START ---")
    print(f"Sending POST request to: {url}")
    print(f"Payload (title only): {title}")
    print(f"Payload (desp length): {len(message)} characters")
    print("--- DEBUGGING INFO END ---")
    # --- Debugging Info End ---

    try:
        response = requests.post(url, data=data, timeout=30) # 增加超时时间
        response.raise_for_status() # 检查 HTTP 错误
        result_text = response.text
        result_json = response.json()
        
        # --- Debugging Info Start ---
        print("--- DEBUGGING INFO START ---")
        print(f"ServerChan Response Status Code: {response.status_code}")
        print(f"ServerChan Raw Response Text: {result_text}")
        print(f"ServerChan Parsed JSON: {result_json}")
        print("--- DEBUGGING INFO END ---")
        # --- Debugging Info End ---

        if result_json.get("code") == 0: # Server酱成功返回码
            print("SUCCESS: Message sent successfully via ServerChan!")
            return True
        else:
            print(f"WARNING: ServerChan returned non-zero code: {result_json.get('code')}")
            print(f"ServerChan Error Message: {result_json.get('message', 'Unknown error')}")
            return False
    except requests.exceptions.Timeout:
        print(f"ERROR: Request to ServerChan timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network or HTTP error occurred when sending to ServerChan: {e}")
        return False
    except ValueError: # JSON decode error
         print(f"ERROR: ServerChan response is not valid JSON: {response.text if 'response' in locals() else 'Response object not available'}")
         return False


def main():
    print("Starting daily tech news fetch process...")

    # 1. 抓取资讯
    recent_stories = get_recent_stories()

    # 2. 构造要发送的消息
    if recent_stories:
        message = "\n".join(recent_stories)
        # 可选：添加一些说明文字
        # message = f"过去24小时热门科技资讯:\n\n{message}"
    else:
        message = "" # 如果没有抓取到，则发送默认消息

    # 3. 推送消息
    success = send_to_wechat(message)

    if success:
        print("Process completed successfully.")
    else:
        print("Process failed.")
        # exit(1) # 可选：失败时退出非零状态，这在 CI/CD 中常用，此处非必需


if __name__ == "__main__":
    main()
