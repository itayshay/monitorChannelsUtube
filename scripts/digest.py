import feedparser
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
import os

# --- CONFIG ---
CHANNEL_IDS = [
    "UCxxxxxxxxxxxxxxxxxxxxxx",  # Channel 1 name
    "UCyyyyyyyyyyyyyyyyyyyyyy",  # Channel 2 name
]
GMAIL_USER = os.environ["GMAIL_USER"]        # your@gmail.com
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"] # app password
TO_EMAIL = os.environ["GMAIL_USER"]           # send to yourself
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def fetch_new_videos(channel_id):
    """Fetch videos published in the last 24 hours from a channel's RSS feed."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    new_videos = []
    for entry in feed.entries:
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if published >= cutoff:
            new_videos.append({
                "title": entry.title,
                "link": entry.link,
                "description": entry.get("summary", "No description available."),
                "channel": feed.feed.title,
                "published": published.strftime("%Y-%m-%d %H:%M UTC")
            })
    return new_videos


def summarize_with_claude(videos):
    """Send video list to Claude and get a summary."""
    if not videos:
        return "No new videos in the last 24 hours."

    video_text = ""
    for v in videos:
        video_text += f"\nChannel: {v['channel']}\nTitle: {v['title']}\nURL: {v['link']}\nDescription: {v['description'][:300]}\nPublished: {v['published']}\n---"

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": f"Here are new YouTube videos from the last 24 hours. Give me a short, friendly summary of each one (2-3 sentences max per video), grouped by channel:\n\n{video_text}"
            }]
        }
    )
    return response.json()["content"][0]["text"]


def send_email(subject, body):
    """Send email via Gmail SMTP."""
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print("Email sent!")


def main():
    all_videos = []
    for channel_id in CHANNEL_IDS:
        videos = fetch_new_videos(channel_id)
        all_videos.extend(videos)
        print(f"Found {len(videos)} new videos from channel {channel_id}")

    summary = summarize_with_claude(all_videos)

    today = datetime.now().strftime("%B %d, %Y")
    send_email(
        subject=f"📺 Your YouTube Daily Digest — {today}",
        body=summary
    )


if __name__ == "__main__":
    main()
