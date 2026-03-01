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

def get_database_pages(database_id, filter_criteria=None):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {}
    if filter_criteria:
        payload["filter"] = filter_criteria

    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error querying database: {response.text}")
        return []

    return response.json().get("results", [])

def get_page_blocks(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error getting blocks: {response.text}")
        return []
    return response.json().get("results", [])

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

def block_to_markdown(block, image_prefix="blog/images", extract_images_list=None):
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
            text = "".join([t["plain_text"] for t in rich_text])
            content = f"> {text}\n\n"

    # Add more block types as needed (to_do, toggle, callout, etc.)
    
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
        # Add other standard Hugo front matter fields here
    }
    
    # Convert Page Content
    blocks = get_page_blocks(page["id"])
    markdown_content = ""
    images_list = [] if extract_images else None
    
    for block in blocks:
        markdown_content += block_to_markdown(block, image_prefix, extract_images_list=images_list)
        
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
