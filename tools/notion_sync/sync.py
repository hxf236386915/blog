import os
import sys
import requests
import yaml
from datetime import datetime
from slugify import slugify

# Configuration
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
CONTENT_DIR = "content/blog"  # Adjust if your content is elsewhere

if not NOTION_TOKEN or not DATABASE_ID:
    print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID environment variables.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_database_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    # Try filtering by '发布状态' first, as user confirmed this field name
    # Update: Based on API response, field is '发布状态' and type is 'select' (not 'status' type, but 'select' type behaving like status)
    payload = {
        "filter": {
            "property": "发布状态",
            "select": {
                "equals": "Published"
            }
        }
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error querying database with 'select' filter: {response.text}")
        # Fallback: maybe it is a status type after all? Or user changed it.
        # But from logs, it is type 'select'.
        return []

    return response.json().get("results", [])

def get_page_blocks(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error getting blocks: {response.text}")
        return []
    return response.json().get("results", [])

def block_to_markdown(block):
    btype = block["type"]
    content = ""
    
    if btype == "paragraph":
        rich_text = block["paragraph"]["rich_text"]
        if rich_text:
            content = "".join([t["plain_text"] for t in rich_text]) + "\n\n"
        else:
            content = "\n"
            
    elif btype == "heading_1":
        rich_text = block["heading_1"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"# {text}\n\n"
            
    elif btype == "heading_2":
        rich_text = block["heading_2"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"## {text}\n\n"
            
    elif btype == "heading_3":
        rich_text = block["heading_3"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"### {text}\n\n"
            
    elif btype == "bulleted_list_item":
        rich_text = block["bulleted_list_item"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"- {text}\n"
            
    elif btype == "numbered_list_item":
        rich_text = block["numbered_list_item"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"1. {text}\n"
            
    elif btype == "code":
        rich_text = block["code"]["rich_text"]
        language = block["code"]["language"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"```{language}\n{text}\n```\n\n"
            
    elif btype == "image":
        # Note: Notion images have expiry times. For a robust solution, 
        # you should download images to local assets.
        # This is a simplified version linking directly.
        if "file" in block["image"]:
            url = block["image"]["file"]["url"]
        elif "external" in block["image"]:
            url = block["image"]["external"]["url"]
        else:
            url = ""
        
        caption = ""
        if block["image"]["caption"]:
            caption = "".join([t["plain_text"] for t in block["image"]["caption"]])
            
        if url:
            content = f"![{caption}]({url})\n\n"

    elif btype == "quote":
        rich_text = block["quote"]["rich_text"]
        if rich_text:
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"> {text}\n\n"

    # Add more block types as needed (to_do, toggle, callout, etc.)
    
    return content

def process_page(page):
    props = page["properties"]
    
    # Extract Title
    title_prop = props.get("Name") or props.get("Title") or props.get("名称")
    if not title_prop or not title_prop["title"]:
        print("Skipping page without title")
        return
    title = "".join([t["plain_text"] for t in title_prop["title"]])
    
    # Extract Date
    date_prop = props.get("Date") or props.get("日期")
    if date_prop and date_prop["date"]:
        date_str = date_prop["date"]["start"]
    else:
        date_str = page["created_time"]
    
    # Extract Tags
    tags = []
    tags_prop = props.get("Tags") or props.get("标签")
    if tags_prop and tags_prop["multi_select"]:
        tags = [t["name"] for t in tags_prop["multi_select"]]

    # Extract Categories (分类)
    categories = []
    cats_prop = props.get("Category") or props.get("Categories") or props.get("分类")
    if cats_prop:
        if cats_prop["type"] == "multi_select":
             categories = [t["name"] for t in cats_prop["multi_select"]]
        elif cats_prop["type"] == "select" and cats_prop["select"]:
             categories = [cats_prop["select"]["name"]]
        
    # Generate Slug/Filename
    slug_prop = props.get("Slug") or props.get("URL别名")
    if slug_prop and slug_prop["rich_text"]:
        slug = "".join([t["plain_text"] for t in slug_prop["rich_text"]])
    else:
        slug = slugify(title)
        
    filename = f"{slug}.md"
    filepath = os.path.join(CONTENT_DIR, filename)
    
    # Prepare Front Matter
    front_matter = {
        "title": title,
        "date": date_str,
        "draft": False,
        "tags": tags,
        "categories": categories,
        # Add other standard Hugo front matter fields here
    }
    
    # Convert Page Content
    blocks = get_page_blocks(page["id"])
    markdown_content = ""
    for block in blocks:
        markdown_content += block_to_markdown(block)
        
    # Write File
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True, default_flow_style=False)
        f.write("---\n\n")
        f.write(markdown_content)
        
    print(f"Synced: {filename}")

def main():
    if not os.path.exists(CONTENT_DIR):
        os.makedirs(CONTENT_DIR)
        
    pages = get_database_pages()
    print(f"Found {len(pages)} published pages.")
    
    for page in pages:
        try:
            process_page(page)
        except Exception as e:
            print(f"Error processing page {page['id']}: {e}")

if __name__ == "__main__":
    main()
