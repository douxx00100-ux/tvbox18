# -*- coding: utf-8 -*-
# 星空中文影院 TVBox 四壳通用 Python Spider
# 站点: https://ro12jq5k.wuaixkw5.sbs/
# 结构: 自定义CMS(xinxin模板), 分类/t/{id}_{page}.html, 详情/s/{id}.html
# 播放页/s-p/{id}-{sid}-{nid}.html, m3u8在JS中为转义字符串(需去转义)
# 视频卡片: 封面在style=background-image:url(), 标题在a的title属性

import re
import json
import urllib.parse

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def __init__(self):
            self.extend = {}

# ==================== 未成年过滤 ====================
MINOR_KEYWORDS = ['萝莉', '幼女', '少女', '童', 'teen', 'loli', 'schoolgirl', '未成年']

def is_minor(text):
    if not text:
        return False
    t = text.lower()
    return any(kw.lower() in t for kw in MINOR_KEYWORDS)

# ==================== 分类配置 (49个, 已过滤id=3萝莉) ====================
CATEGORIES = [
    {"type_id": "1", "type_name": "国产"},
    {"type_id": "2", "type_name": "网红"},
    {"type_id": "4", "type_name": "大秀"},
    {"type_id": "5", "type_name": "探花"},
    {"type_id": "6", "type_name": "自拍"},
    {"type_id": "7", "type_name": "乱伦毁三观"},
    {"type_id": "8", "type_name": "迷奸强奸"},
    {"type_id": "9", "type_name": "传媒"},
    {"type_id": "10", "type_name": "反差婊"},
    {"type_id": "11", "type_name": "网爆门"},
    {"type_id": "12", "type_name": "偷拍"},
    {"type_id": "13", "type_name": "福利姬"},
    {"type_id": "14", "type_name": "吃瓜"},
    {"type_id": "15", "type_name": "学生妹"},
    {"type_id": "16", "type_name": "人兽"},
    {"type_id": "17", "type_name": "人妖"},
    {"type_id": "18", "type_name": "OnlyFans"},
    {"type_id": "20", "type_name": "喷水"},
    {"type_id": "21", "type_name": "裸贷"},
    {"type_id": "22", "type_name": "性虐"},
    {"type_id": "23", "type_name": "AI换脸"},
    {"type_id": "24", "type_name": "无码"},
    {"type_id": "25", "type_name": "中字"},
    {"type_id": "26", "type_name": "欧美"},
    {"type_id": "27", "type_name": "动漫"},
    {"type_id": "28", "type_name": "三级片"},
    {"type_id": "29", "type_name": "AV解说"},
    {"type_id": "30", "type_name": "兄妹"},
    {"type_id": "31", "type_name": "母子"},
    {"type_id": "32", "type_name": "小姨"},
    {"type_id": "33", "type_name": "嫂子"},
    {"type_id": "34", "type_name": "野外"},
    {"type_id": "35", "type_name": "换妻"},
    {"type_id": "36", "type_name": "儿媳"},
    {"type_id": "37", "type_name": "下海"},
    {"type_id": "38", "type_name": "瑜伽裤"},
    {"type_id": "39", "type_name": "兽耳系列"},
    {"type_id": "40", "type_name": "多人群P"},
    {"type_id": "41", "type_name": "Cosplay"},
    {"type_id": "50", "type_name": "有码"},
    {"type_id": "51", "type_name": "黑料"},
    {"type_id": "52", "type_name": "技师"},
    {"type_id": "53", "type_name": "绿帽"},
    {"type_id": "54", "type_name": "丝足"},
    {"type_id": "55", "type_name": "偷情"},
    {"type_id": "56", "type_name": "校园"},
    {"type_id": "57", "type_name": "撸管"},
    {"type_id": "58", "type_name": "制服"},
    {"type_id": "59", "type_name": "黑巨炮"},
]


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.siteUrl = "https://ro12jq5k.wuaixkw5.sbs"
        self.rawSite = "https://ro12jq5k.wuaixkw5.sbs"
        self.HOST = self.siteUrl
        self._session = None

    def init(self, extend=""):
        if extend and isinstance(extend, str):
            try:
                self.extend = json.loads(extend)
            except Exception:
                self.extend = {}
        elif isinstance(extend, dict):
            self.extend = extend
        else:
            self.extend = {}
        if self.extend.get("siteUrl"):
            self.siteUrl = self.extend["siteUrl"]
            self.HOST = self.siteUrl
        if self.extend.get("proxy"):
            self.siteUrl = self.extend["proxy"]
            self.HOST = self.siteUrl

    # ==================== HTTP ====================
    def _get_session(self):
        if self._session is None:
            if HAS_CURL_CFFI:
                self._session = curl_requests.Session(impersonate="chrome131")
            else:
                import requests as req_lib
                self._session = req_lib.Session()
                self._session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                })
        return self._session

    def _fetch(self, url, timeout=15):
        session = self._get_session()
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    def _abs_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.siteUrl + url
        return self.siteUrl + "/" + url

    # ==================== 解析视频列表 ====================
    def _parse_videos(self, html):
        """从HTML中解析视频列表 (xinxin模板, 封面在style=background-image:url(), 标题在a的title属性)"""
        vod_list = []
        # 匹配 <a class="pic" href="/s/{id}.html" title="TITLE" style="background-image:url(COVER)">
        pattern = r'<a[^>]*class="pic"[^>]*href="/s/(\d+)\.html"[^>]*title="([^"]*)"[^>]*style="background-image:url\(([^)]+)\)"'
        for vid, title, cover in re.findall(pattern, html):
            if not title or is_minor(title):
                continue
            vod_list.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._abs_url(cover),
                "vod_remarks": "",
            })
        # 兜底: 匹配顺序不同的情况
        if not vod_list:
            pattern2 = r'<a[^>]*href="/s/(\d+)\.html"[^>]*title="([^"]*)"[^>]*style="background-image:url\(([^)]+)\)"'
            for vid, title, cover in re.findall(pattern2, html):
                if not title or is_minor(title):
                    continue
                vod_list.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._abs_url(cover),
                    "vod_remarks": "",
                })
        return vod_list

    # ==================== 1. homeContent ====================
    def homeContent(self, *args):
        result = {}
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in CATEGORIES]
        result["class"] = classes
        filters = {}
        for c in CATEGORIES:
            filters[c["type_id"]] = []
        result["filters"] = filters
        html = self._fetch(self.siteUrl + "/")
        result["list"] = self._parse_videos(html) if html else []
        return result

    # ==================== 2. categoryContent ====================
    def categoryContent(self, tid, page=1, *args):
        result = {}
        page = int(page)
        if page <= 1:
            url = f"{self.siteUrl}/t/{tid}.html"
        else:
            url = f"{self.siteUrl}/t/{tid}_{page}.html"
        html = self._fetch(url)
        vod_list = self._parse_videos(html)
        # 分页
        pages = re.findall(r'/t/' + re.escape(tid) + r'_(\d+)\.html', html)
        max_page = max(int(p) for p in pages) if pages else 999
        result["page"] = page
        result["pagecount"] = max_page
        result["limit"] = 16
        result["total"] = max_page * 16
        result["list"] = vod_list
        return result

    # ==================== 3. detailContent ====================
    def detailContent(self, ids, *args):
        result = {}
        vod_list = []
        if isinstance(ids, str):
            ids = [ids]
        for vod_id in ids:
            if not vod_id:
                continue
            # 详情页
            html = self._fetch(f"{self.siteUrl}/s/{vod_id}.html")
            if not html:
                continue
            # 标题
            title_m = re.search(r'<title>(.*?)</title>', html, re.S)
            vod_name = ""
            if title_m:
                vod_name = title_m.group(1).split('_星空中文')[0].strip()
                vod_name = vod_name.split('在线播放')[0].strip()
            if not vod_name:
                # 从卡片title属性
                title_attr_m = re.search(r'href="/s/' + vod_id + r'\.html"[^>]*title="([^"]+)"', html)
                if title_attr_m:
                    vod_name = title_attr_m.group(1)
            if is_minor(vod_name):
                continue
            # 封面
            cover_m = re.search(r'background-image:url\(([^)]+)\)', html)
            vod_pic = cover_m.group(1) if cover_m else ""
            # 播放链接 /s-p/{id}-{sid}-{nid}.html
            play_links = re.findall(r'/s-p/(\d+)-(\d+)-(\d+)\.html', html)
            vod_play_from = ""
            vod_play_url = ""
            if play_links:
                episodes = []
                for pid, sid, nid in play_links:
                    play_url = f"{self.siteUrl}/s-p/{pid}-{sid}-{nid}.html"
                    episodes.append(f"第{nid}集${play_url}")
                vod_play_from = "HD高清"
                vod_play_url = "#".join(episodes)
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": self._abs_url(vod_pic),
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            })
        result["list"] = vod_list
        return result

    # ==================== 4. playerContent ====================
    def playerContent(self, flag, id, vipFlags=None, *args):
        result = {}
        play_url = id
        if not play_url.startswith("http"):
            play_url = self._abs_url(play_url)
        m3u8_url = play_url
        # 如果是播放页URL, 抓取获取m3u8
        if '/s-p/' in play_url:
            html = self._fetch(play_url)
            if html:
                # m3u8在JS中为转义字符串 https:\/\/...\/index.m3u8
                m3u8_m = re.search(r'(https?:\\?/\\?/[^\s"\']+\.m3u8[^\s"\']*)', html)
                if m3u8_m:
                    m3u8_url = m3u8_m.group(1).replace('\\/', '/').replace('\\', '')
                # 兜底: 直接找m3u8
                if not m3u8_url or '.m3u8' not in m3u8_url:
                    m3u8_direct = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                    if m3u8_direct:
                        m3u8_url = m3u8_direct.group(1)
        result["parse"] = 0
        result["jx"] = 0
        result["url"] = m3u8_url
        result["header"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }
        return result

    # ==================== 5. searchContent ====================
    def searchContent(self, key, page=1, *args):
        result = {}
        page = int(page)
        key_enc = urllib.parse.quote(key)
        # 尝试多种搜索格式
        html = ""
        for url in [
            f"{self.siteUrl}/s/{key_enc}.html",
            f"{self.siteUrl}/search/wd/{key_enc}.html",
            f"{self.siteUrl}/search.html?wd={key_enc}",
            f"{self.siteUrl}/?wd={key_enc}",
        ]:
            html = self._fetch(url)
            if html and '/s-p/' in html:
                break
        vod_list = self._parse_videos(html) if html else []
        result["page"] = page
        result["pagecount"] = 1
        result["limit"] = 16
        result["total"] = len(vod_list)
        result["list"] = vod_list
        return result

    # ==================== 6. localProxy ====================
    def localProxy(self, param):
        try:
            if isinstance(param, str):
                params = urllib.parse.parse_qs(param)
            else:
                params = param or {}
            url = params.get("url", [""])[0] if isinstance(params, dict) else ""
            if not url:
                return [404, "text/plain", ""]
            html = self._fetch(url, timeout=10)
            if not html:
                return [404, "text/plain", "fetch failed"]
            cleaned = self._clean_m3u8(html, url)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception:
            return [404, "text/plain", ""]

    def _clean_m3u8(self, content, base_url=""):
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if self._is_ad_segment(line):
                continue
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                cleaned.append("#EXT-X-MEDIA-SEQUENCE:0")
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _is_ad_segment(self, line):
        if not line or line.startswith("#"):
            return False
        ad_keywords = ["ad", "gg", "adv", "preroll", "片头", "广告"]
        return any(kw in line.lower() for kw in ad_keywords)

    # ==================== 7. 其他接口 ====================
    def isVideoFormat(self, url):
        return any(url.endswith(ext) for ext in [".m3u8", ".mp4", ".mkv", ".avi", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def getDependence(self):
        return "星空中文影院 Spider loaded"

    def getName(self):
        return "星空中文影院"

    def destroy(self):
        self._session = None
