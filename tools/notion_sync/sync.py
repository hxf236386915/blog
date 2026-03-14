import os
import sys
import requests
import yaml
import hashlib
from datetime import datetime
from slugify import slugify
from urllib.parse import urlparse
from qiniu import Auth, put_data

# Configuration
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
BLOG_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
FRAGMENTS_DATABASE_ID = os.environ.get("NOTION_FRAGMENTS_DATABASE_ID")

BLOG_CONTENT_DIR = "content/chinese/blog"
FRAGMENTS_CONTENT_DIR = "content/chinese/fragments"
STATIC_IMG_DIR = "static/images"
IMG_URL_PREFIX = "/images"

# Qiniu Configuration
QINIU_ACCESS_KEY = os.environ.get("QINIU_ACCESS_KEY")
QINIU_SECRET_KEY = os.environ.get("QINIU_SECRET_KEY")
QINIU_BUCKET_NAME = os.environ.get("QINIU_BUCKET_NAME")
QINIU_DOMAIN = os.environ.get("QINIU_DOMAIN")

if not NOTION_TOKEN or not BLOG_DATABASE_ID:
    print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID environment variables.")
    sys.exit(1)

# Initialize Qiniu Auth
q = None
if QINIU_ACCESS_KEY and QINIU_SECRET_KEY:
    q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
    print("Qiniu SDK initialized.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

NOTION_PAGE_SIZE = 100

def _plain_text_from_rich_text(rich_text):
    if not rich_text:
        return ""
    return "".join([t.get("plain_text", "") for t in rich_text]).strip()

def _render_rich_text(rich_text):
    if not rich_text:
        return ""
    parts = []
    for t in rich_text:
        text = t.get("plain_text", "")
        href = t.get("href")
        if href and text:
            parts.append(f"[{text}]({href})")
        else:
            parts.append(text)
    return "".join(parts)

def _extract_single_text_property(props, keys):
    for key in keys:
        prop = props.get(key)
        if not prop:
            continue

        ptype = prop.get("type")
        if ptype == "people":
            people = prop.get("people") or []
            names = [p.get("name", "").strip() for p in people if p.get("name")]
            if not names:
                continue
            return names[0]

        if ptype == "select":
            sel = prop.get("select")
            if sel and sel.get("name"):
                return str(sel["name"]).strip()
            continue

        if ptype == "multi_select":
            items = prop.get("multi_select") or []
            names = [i.get("name", "").strip() for i in items if i.get("name")]
            if not names:
                continue
            return names[0]

        if ptype == "rich_text":
            text = _plain_text_from_rich_text(prop.get("rich_text"))
            if text:
                return text
            continue

        if ptype == "title":
            text = _plain_text_from_rich_text(prop.get("title"))
            if text:
                return text
            continue

        if ptype == "email":
            email = prop.get("email")
            if email:
                return str(email).strip()
            continue

        if ptype == "url":
            url = prop.get("url")
            if url:
                return str(url).strip()
            continue

    return ""

def get_database_pages(database_id, filter_criteria=None):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": NOTION_PAGE_SIZE}
    if filter_criteria:
        payload["filter"] = filter_criteria

    all_results = []
    start_cursor = None

    while True:
        if start_cursor:
            payload["start_cursor"] = start_cursor
        elif "start_cursor" in payload:
            del payload["start_cursor"]

        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code != 200:
            print(f"Error querying database: {response.text}")
            return []

        data = response.json()
        all_results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        start_cursor = data.get("next_cursor")
        if not start_cursor:
            break

    return all_results

def _get_block_children(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {"page_size": NOTION_PAGE_SIZE}

    all_results = []
    start_cursor = None

    while True:
        if start_cursor:
            params["start_cursor"] = start_cursor
        elif "start_cursor" in params:
            del params["start_cursor"]

        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"Error getting blocks: {response.text}")
            return []

        data = response.json()
        all_results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        start_cursor = data.get("next_cursor")
        if not start_cursor:
            break

    return all_results

def get_page_blocks(block_id):
    blocks = _get_block_children(block_id)
    for block in blocks:
        if block.get("has_children"):
            block["_children"] = get_page_blocks(block["id"])
    return blocks

def _indent_markdown(markdown, spaces):
    if not markdown:
        return ""
    prefix = " " * spaces
    return "\n".join([f"{prefix}{line}" if line.strip() else line for line in markdown.splitlines()]) + "\n"

def download_image(url, prefix="blog/images"):
    """
    Downloads an image from the given URL and uploads it to Qiniu OSS.
    If Qiniu is not configured, saves it to the static/images directory.
    Returns the URL to be used in the markdown.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            ext = ".jpg" # default
            if "image/png" in content_type:
                ext = ".png"
            elif "image/jpeg" in content_type:
                ext = ".jpg"
            elif "image/gif" in content_type:
                ext = ".gif"
            elif "image/webp" in content_type:
                ext = ".webp"
            else:
                parsed = urlparse(url)
                path = parsed.path
                if "." in path:
                    ext = os.path.splitext(path)[1]

            content = response.content
            file_hash = hashlib.md5(content).hexdigest()
            filename = f"{file_hash}{ext}"

            # Try uploading to Qiniu if configured
            if q and QINIU_BUCKET_NAME and QINIU_DOMAIN:
                try:
                    # The key to save in Qiniu
                    key = f"{prefix}/{filename}"
                    # Check if file exists in Qiniu - skipping for now, put_data will overwrite if exists
                    token = q.upload_token(QINIU_BUCKET_NAME, key, 3600)
                    ret, info = put_data(token, key, content)
                    
                    if info.status_code == 200:
                        # Force use HTTPS as user requested (GitHub Pages requires HTTPS)
                        qiniu_url = f"https://{QINIU_DOMAIN}/{key}"
                            
                        print(f"Uploaded to Qiniu: {qiniu_url}")
                        return qiniu_url
                    else:
                        print(f"Qiniu upload failed, falling back to local: {info}")
                except Exception as qe:
                    print(f"Error during Qiniu upload: {qe}")

            # Fallback to local storage
            if not os.path.exists(STATIC_IMG_DIR):
                os.makedirs(STATIC_IMG_DIR)
            filepath = os.path.join(STATIC_IMG_DIR, filename)
            if not os.path.exists(filepath):
                with open(filepath, "wb") as f:
                    f.write(content)
                print(f"Saved local image: {filename}")
            return f"{IMG_URL_PREFIX}/{filename}"
        else:
            print(f"Failed to download image: {url} (Status: {response.status_code})")
            return url
    except Exception as e:
        print(f"Error downloading image: {e}")
        return url

def blocks_to_markdown(blocks, image_prefix="blog/images", extract_images_list=None):
    markdown_content = ""
    for block in blocks:
        markdown_content += block_to_markdown(block, image_prefix, extract_images_list=extract_images_list)
    return markdown_content

def block_to_markdown(block, image_prefix="blog/images", extract_images_list=None):
    btype = block["type"]
    content = ""
    
    if btype == "paragraph":
        rich_text = block["paragraph"]["rich_text"]
        text = _render_rich_text(rich_text)
        content = f"{text}\n\n" if text else "\n"
            
    elif btype == "heading_1":
        rich_text = block["heading_1"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"# {text}\n\n"
            
    elif btype == "heading_2":
        rich_text = block["heading_2"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"## {text}\n\n"
            
    elif btype == "heading_3":
        rich_text = block["heading_3"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"### {text}\n\n"
            
    elif btype == "bulleted_list_item":
        rich_text = block["bulleted_list_item"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"- {text}\n"
            
    elif btype == "numbered_list_item":
        rich_text = block["numbered_list_item"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"1. {text}\n"
            
    elif btype == "code":
        rich_text = block["code"]["rich_text"]
        language = block["code"]["language"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"```{language}\n{text}\n```\n\n"
            
    elif btype == "image":
        if "file" in block["image"]:
            url = block["image"]["file"]["url"]
        elif "external" in block["image"]:
            url = block["image"]["external"]["url"]
        else:
            url = ""
        
        caption = ""
        if block["image"]["caption"]:
            caption = _render_rich_text(block["image"]["caption"])
            
        if url:
            # Download image and replace URL with local path
            local_url = download_image(url, image_prefix)
            
            if extract_images_list is not None:
                extract_images_list.append({"url": local_url, "caption": caption})
                content = ""
            else:
                content = f"![{caption}]({local_url})\n\n"

    elif btype == "quote":
        rich_text = block["quote"]["rich_text"]
        if rich_text:
            text = _render_rich_text(rich_text)
            content = f"> {text}\n\n"

    elif btype == "divider":
        content = "---\n\n"

    elif btype == "to_do":
        rich_text = block["to_do"]["rich_text"]
        checked = bool(block["to_do"].get("checked"))
        text = _render_rich_text(rich_text)
        mark = "x" if checked else " "
        content = f"- [{mark}] {text}\n"

    elif btype == "callout":
        rich_text = block["callout"]["rich_text"]
        icon = block["callout"].get("icon") or {}
        emoji = icon.get("emoji") if icon.get("type") == "emoji" else ""
        text = _render_rich_text(rich_text)
        prefix = f"{emoji} " if emoji else ""
        content = f"> {prefix}{text}\n\n"

    elif btype == "toggle":
        rich_text = block["toggle"]["rich_text"]
        summary = _render_rich_text(rich_text)
        children = block.get("_children") or []
        children_md = blocks_to_markdown(children, image_prefix, extract_images_list=extract_images_list)
        content = f"<details><summary>{summary}</summary>\n\n{children_md}\n</details>\n\n"

    elif btype == "bookmark":
        url = block["bookmark"].get("url")
        if url:
            content = f"[{url}]({url})\n\n"
    
    children = block.get("_children") or []
    if children and btype in {"bulleted_list_item", "numbered_list_item", "to_do"}:
        children_md = blocks_to_markdown(children, image_prefix, extract_images_list=extract_images_list)
        content += _indent_markdown(children_md, 2)
    elif children and btype not in {"toggle"}:
        content += blocks_to_markdown(children, image_prefix, extract_images_list=extract_images_list)

    return content

def process_page(page, content_dir, image_prefix="blog/images", extract_images=False):
    props = page["properties"]
    
    # Extract Title
    title = ""
    title_prop = props.get("Name") or props.get("Title") or props.get("名称")
    if title_prop and title_prop.get("title"):
        title = "".join([t["plain_text"] for t in title_prop["title"]])
    
    if not title:
        # Fallback for empty title (common in fragments)
        print("Page has no title, using created_time as title.")
        title = page["created_time"]
    
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

    author = _extract_single_text_property(props, ["Author", "author", "作者", "作者信息"])
        
    # Generate Slug/Filename
    slug_prop = props.get("Slug") or props.get("URL别名")
    if slug_prop and slug_prop["rich_text"]:
        slug = "".join([t["plain_text"] for t in slug_prop["rich_text"]])
    else:
        slug = slugify(title)
        
    filename = f"{slug}.md"
    filepath = os.path.join(content_dir, filename)
    
    # Prepare Front Matter
    front_matter = {
        "title": title,
        "date": date_str,
        "draft": False,
        "tags": tags,
        "categories": categories,
    }
    if author:
        front_matter["author"] = author
    
    # Convert Page Content
    blocks = get_page_blocks(page["id"])
    images_list = [] if extract_images else None
    markdown_content = blocks_to_markdown(blocks, image_prefix, extract_images_list=images_list)
        
    if images_list:
        front_matter["images"] = [img["url"] for img in images_list]
        front_matter["gallery"] = images_list
        
    # Write File
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True, default_flow_style=False)
        f.write("---\n\n")
        f.write(markdown_content)
        
    print(f"Synced: {filename}")

def sync_database(database_id, content_dir, label, filter_criteria=None, image_prefix="blog/images", extract_images=False):
    if not database_id:
        print(f"[{label}] Database ID not set, skipping.")
        return

    if not os.path.exists(content_dir):
        os.makedirs(content_dir)

    pages = get_database_pages(database_id, filter_criteria)
    print(f"[{label}] Found {len(pages)} published pages.")

    for page in pages:
        try:
            process_page(page, content_dir, image_prefix, extract_images)
        except Exception as e:
            print(f"[{label}] Error processing page {page['id']}: {e}")

def main():
    blog_filter = {
        "property": "发布状态",
        "select": {
            "equals": "Published"
        }
    }
    sync_database(BLOG_DATABASE_ID, BLOG_CONTENT_DIR, "blog", blog_filter, "blog/images", extract_images=False)
    sync_database(FRAGMENTS_DATABASE_ID, FRAGMENTS_CONTENT_DIR, "fragments", None, "fragments/images", extract_images=True)

if __name__ == "__main__":
    main()
