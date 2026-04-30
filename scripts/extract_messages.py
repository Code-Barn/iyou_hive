import json
import re
import sqlite3
from datetime import datetime

# 1. SETUP
db_path = "chat_backup.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

target_ids = (
    "violettemichele@icloud.com",
    "+18152068357",
    "violette@iyou.me",
    "+18157614877",
)


# 2. THE DECODER
def decode_typed_stream(blob):
    if not blob:
        return ""
    try:
        parts = blob.split(b"NSString")
        if len(parts) < 2:
            return ""
        raw_text = parts[-1][6:].decode("utf-8", errors="ignore")
        match = re.search(r'[^\w\s\d.,!?\'"()\-❤️💯🙏😊👍🙌✨🔥😢😡😎🤔/:]', raw_text)
        clean_text = raw_text[: match.start()] if match else raw_text
        clean_text = clean_text.strip()
        if len(clean_text) == 1 and clean_text.lower() not in ("i", "?", "a"):
            return ""
        return clean_text
    except:
        return ""


# 3. THE UPDATED QUERY (Now with Attachments)
placeholders = ", ".join(["?"] * len(target_ids))
query = f"""
SELECT
    m.date,
    h.id,
    m.text,
    m.attributedBody,
    m.is_from_me,
    a.filename  -- This grabs the file path/name from the attachment table
FROM message m
LEFT JOIN handle h ON m.handle_id = h.rowid
LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
LEFT JOIN chat c ON cmj.chat_id = c.rowid
LEFT JOIN message_attachment_join maj ON m.rowid = maj.message_id
LEFT JOIN attachment a ON maj.attachment_id = a.rowid
WHERE h.id IN ({placeholders}) OR c.chat_identifier IN ({placeholders})
ORDER BY m.date ASC;
"""

# 4. EXECUTION
combined_messages = []
cursor.execute(query, target_ids + target_ids)
rows = cursor.fetchall()

for row in rows:
    date_raw, handle_id, text, attr_body, is_from_me, attachment_path = row
    unix_ts = (date_raw / 1000000000) + 978307200
    message_content = text if text else decode_typed_stream(attr_body)

    # Clean up the attachment path (it often looks like ~/Library/...)
    file_placeholder = ""
    if attachment_path:
        file_placeholder = attachment_path.split("/")[
            -1
        ]  # Just get the "IMG_123.JPG" part

    clean_content = message_content.replace("\ufffc", "").strip()

    # If it's a Tapback/Reaction with no text but HAS an attachment, we keep it
    if clean_content != "" or file_placeholder != "":
        sender_label = (
            "Me" if is_from_me == 1 else (handle_id if handle_id else "Violette")
        )

        msg_entry = {
            "unix_ts": unix_ts,
            "timestamp": datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M:%S"),
            "sender": sender_label,
            "message": message_content.strip(),
        }

        if file_placeholder:
            msg_entry["attachment"] = file_placeholder

        combined_messages.append(msg_entry)

# 5. DEDUPLICATION & SAVE
seen = set()
final_list = []
sorted_messages = sorted(combined_messages, key=lambda x: x["unix_ts"])

for msg in sorted_messages:
    fingerprint = (
        msg["timestamp"],
        msg["sender"],
        msg.get("message", ""),
        msg.get("attachment", ""),
    )
    if fingerprint not in seen:
        seen.add(fingerprint)
        del msg["unix_ts"]
        final_list.append(msg)

with open("Violette_Final_Timeline_With_Assets.json", "w", encoding="utf-8") as f:
    json.dump(final_list, f, indent=4, ensure_ascii=False)

print(
    f"Extraction complete! {len(final_list)} messages (with attachment placeholders) saved."
)
