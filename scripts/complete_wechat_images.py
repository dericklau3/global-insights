#!/usr/bin/env python3
"""Backfill existing WeChat Markdown articles from verified Wikimedia Commons source files.
Only edits the listed existing articles, image assets and date README.
On failures leaves the text unchanged and reports failed entries to CI logs.
"""
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
import requests
import cairosvg
from PIL import Image, ImageOps, ImageFile
Image.MAX_IMAGE_PIXELS = 100_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = True
USER_AGENT = "global-insights-image-archiver/1.0 (news image credit tool; GitHub dericklau3/global-insights)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
LICENSE_URLS = {
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}
def commons_file(title):
    api = "https://commons.wikimedia.org/w/api.php"
    for attempt in range(3):
        try:
            q = requests.get(api, headers=HEADERS, params={
                "action": "query", "format":"json", "titles":"File:"+title,
                "prop":"imageinfo", "iiprop":"url|extmetadata", "iiurlwidth":1800
            }, timeout=28)
            q.raise_for_status()
            pages = list(q.json()["query"]["pages"].values())
            record = pages[0].get("imageinfo", [{}])[0]
            url = (record.get("url") if title.lower().endswith(".svg") else (record.get("thumburl") or record.get("url")))
            if not url: raise ValueError("Commons page did not resolve any file")
            return url, record
        except Exception:
            if attempt == 2: raise
            time.sleep(15 * (attempt+1))
def download_image(title):
    url, info = commons_file(title)
    data = requests.get(url, headers=HEADERS, timeout=65)
    data.raise_for_status()
    # The proxy can return a text error with status 200; never save that as media.
    if len(data.content) < 500: raise ValueError("Downloaded image is unexpectedly small")
    typ = data.headers.get("Content-Type","")
    if "html" in typ or data.content.lstrip().startswith(b"<!DOCTYPE"):
        raise ValueError("Downloaded webpage instead of image data")
    if ".svg" in title.lower():
        bitmap = cairosvg.svg2png(bytestring=data.content, output_width=1600)
        image = Image.open(io.BytesIO(bitmap))
    else:
        image = Image.open(io.BytesIO(data.content))
    image.load()
    return image.convert("RGBA"), url, info
def fit_cover(image):
    # Genuine source pixels, cropping and sizing only; no generative scene or text.
    width, height = 1175, 500
    w,h=image.size
    if w / h > 1.55 and w/h < 3.5:
        canvas=ImageOps.fit(image.convert("RGB"), (width,height), method=Image.Resampling.LANCZOS, centering=(0.5,0.48))
    else:
        # Portrait photos / horizontal text logos: retain the real full subject on a neutral surround.
        background=(17,27,42) if w/h < 1.1 else (239,243,247)
        canvas=Image.new("RGB",(width,height),background)
        obj=ImageOps.contain(image,(width-100,height-42),Image.Resampling.LANCZOS)
        px=(width-obj.width)//2; py=(height-obj.height)//2
        canvas.paste(obj, (px,py), mask=obj.getchannel("A"))
    return canvas
def fit_body(image):
    img=image.copy()
    img.thumbnail((1400,1000),Image.Resampling.LANCZOS)
    bg=Image.new("RGB",img.size,(255,255,255))
    bg.paste(img,mask=img.getchannel("A"))
    return bg
def save_jpeg(im,path,quality=86):
    path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path,"JPEG",quality=quality,optimize=True,progressive=True)
def main(manifest_path):
    manifest_file=Path(manifest_path)
    folder=manifest_file.parent
    manifest=json.loads(manifest_file.read_text("utf-8"))
    credits=[]
    complete=0
    failures=[]
    for row in manifest:
        name=row["article"]
        doc=folder/name
        if not doc.is_file():
            failures.append(name+": Markdown missing")
            continue
        topic=row["prefix"]; title=row["commons_file"]
        photo=folder/"assets"/(topic+"_01.jpg")
        cover=folder/"assets"/(topic+"_cover.jpg")
        # Do not re-download successfully archived assets during retry runs.
        if photo.is_file() and cover.is_file() and f"assets/{topic}_01.jpg" in doc.read_text("utf-8"):
            license_url=LICENSE_URLS.get(row["license"],"")
            source_page="https://commons.wikimedia.org/wiki/File:"+quote(title.replace(" ","_"),safe="()'_")
            credits.append(f"- [{name}](./{quote(name)}): [图片出处]({source_page}) · 作者 {row['author']} · {row['license']}"+(f" ([许可条款]({license_url}))" if license_url else "")+f"；已裁切/缩放。 [正文图](assets/{topic}_01.jpg) · [独立封面](assets/{topic}_cover.jpg)。")
            complete+=1
            print("SKIPPED_EXISTING",name,flush=True)
            continue
        try:
            source, actual_url, info=download_image(title)
            if source.width<150 or source.height<100: raise ValueError("Image resolution too low")
            save_jpeg(fit_body(source),photo)
            save_jpeg(fit_cover(source),cover)
            check=Image.open(cover)
            if check.size != (1175,500):raise AssertionError("Bad cover dimensions")
            text=doc.read_text("utf-8")
            if "_cover" in text: raise ValueError("Unexpected cover reference already in Markdown")
            inline=f"assets/{topic}_01.jpg"
            credit=(f"*配图：{row['caption']}；"
                    f"图片：{row['author']}，{row['license']}。"
                    f"资料图片，不代表本次新闻事件的实际现场。*")
            insertion=f"![{row['caption']}]({inline})\n\n{credit}\n\n"
            if inline not in text:
                first_heading=re.search(r"(?m)^## ",text)
                if first_heading: text=text[:first_heading.start()]+insertion+text[first_heading.start():]
                else: text=text+"\n"+insertion
                doc.write_text(text,"utf-8")
            license_url=LICENSE_URLS.get(row["license"],"")
            source_page="https://commons.wikimedia.org/wiki/File:"+quote(title.replace(" ","_"),safe="()'_")
            creditline=(f"- [{name}](./{quote(name)}): "
              f"[图片出处]({source_page}) · 作者 {row['author']} · "
              f"{row['license']}"+(f" ([许可条款]({license_url}))" if license_url else "")
              +f"；已裁切/缩放。 [正文图](assets/{topic}_01.jpg) · [独立封面](assets/{topic}_cover.jpg)。")
            credits.append(creditline)
            complete+=1
            print("COMPLETE",name,source.size,cover.name,flush=True)
            time.sleep(2)
        except Exception as e:
            failures.append(name+": "+str(e))
            print("FAILED",name,repr(e),flush=True)
    readme=folder/"README.md"
    if credits and readme.is_file():
        content=readme.read_text("utf-8")
        # Regenerating is idempotent: replace this specific block only.
        marker="## 图片与封面资源（版权及来源）"
        content=content.split(marker)[0].rstrip()
        content=re.sub(r"\n> 本轮因图片素材核验、版权与二进制上传尚未完成，暂未生成封面或正文配图；不得将文章视为已完成视觉制作的公众号成稿。正文无封面引用与不存在的图片路径。", "", content)
        content+="\n\n"+marker+"\n\n"
        content+="封面为 1175×500 的独立图片，不嵌入正文。图片取自所列 Wikimedia Commons 原始来源，经过裁切/缩放；公司建筑、历史发射等均为**资料图片，不代表本次新闻现场**。\n\n"
        content+="\n".join(credits)+"\n"
        if failures:
            content+="\n**仍待补图：** "+", ".join(failures)+"\n"
        readme.write_text(content,"utf-8")
    print(f"STATUS: {complete}/{len(manifest)} article illustrations & covers successfully saved",flush=True)
    if failures: print("INCOMPLETE:", *failures,sep="\n- ",flush=True)
    if complete==0: sys.exit(1)
if __name__=="__main__":
    if len(sys.argv)!=2:sys.exit("Usage: complete_wechat_images.py <manifest.json>")
    main(sys.argv[1])
