# -*- coding: utf-8 -*-
# 苹果影院 TVBox 四壳通用 Python Spider
# 站点: https://xxkfcaa.xyz/
# 结构: 自定义CMS(mytpl模板), 首页为导航页无视频列表, 分类页10条/页
# 视频: /vod-detail/id-{id}.html -> /vod-play/id-{id}.html, 播放页ckplayer player.php?url=直出m3u8
# 分类: /vod-type/id-{id}-by-time-pg-{page}.html, 搜索: /vod-search/wd-{kw}-by-time-pg-{page}.html

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

# ==================== 分类配置 (过滤未成年后138个) ====================
CATEGORIES = [
    {"type_id": "123", "type_name": "亚洲情色"},
    {"type_id": "124", "type_name": "重口色情"},
    {"type_id": "126", "type_name": "丝袜长腿"},
    {"type_id": "127", "type_name": "卡通动画"},
    {"type_id": "128", "type_name": "女同性恋"},
    {"type_id": "129", "type_name": "制服诱惑"},
    {"type_id": "130", "type_name": "中文字幕"},
    {"type_id": "131", "type_name": "巨乳美乳"},
    {"type_id": "132", "type_name": "强奸乱伦"},
    {"type_id": "133", "type_name": "熟女人妻"},
    {"type_id": "134", "type_name": "欧美性爱"},
    {"type_id": "135", "type_name": "无码专区"},
    {"type_id": "136", "type_name": "国产自拍"},
    {"type_id": "137", "type_name": "国产主播"},
    {"type_id": "138", "type_name": "人兽性交"},
    {"type_id": "304", "type_name": "国产视频"},
    {"type_id": "305", "type_name": "中文字幕"},
    {"type_id": "306", "type_name": "国产传媒"},
    {"type_id": "307", "type_name": "日本有码"},
    {"type_id": "308", "type_name": "日本无码"},
    {"type_id": "309", "type_name": "欧美无码"},
    {"type_id": "310", "type_name": "强奸乱伦"},
    {"type_id": "311", "type_name": "制服诱惑"},
    {"type_id": "312", "type_name": "国产主播"},
    {"type_id": "313", "type_name": "激情动漫"},
    {"type_id": "314", "type_name": "明星换脸"},
    {"type_id": "315", "type_name": "抖阴视频"},
    {"type_id": "316", "type_name": "女优明星"},
    {"type_id": "317", "type_name": "网曝黑料"},
    {"type_id": "318", "type_name": "伦理三级"},
    {"type_id": "319", "type_name": "AV解说"},
    {"type_id": "320", "type_name": "SM调教"},
    {"type_id": "322", "type_name": "极品媚黑"},
    {"type_id": "323", "type_name": "女同性恋"},
    {"type_id": "324", "type_name": "网红头条"},
    {"type_id": "325", "type_name": "人妖系列"},
    {"type_id": "326", "type_name": "韩国主播"},
    {"type_id": "327", "type_name": "VR视角"},
    {"type_id": "329", "type_name": "国产精品"},
    {"type_id": "330", "type_name": "华语AV"},
    {"type_id": "331", "type_name": "黑料吃瓜"},
    {"type_id": "332", "type_name": "欧美"},
    {"type_id": "333", "type_name": "禁漫"},
    {"type_id": "334", "type_name": "学生"},
    {"type_id": "335", "type_name": "乱伦"},
    {"type_id": "336", "type_name": "探花"},
    {"type_id": "337", "type_name": "日本无码"},
    {"type_id": "338", "type_name": "日本有码"},
    {"type_id": "339", "type_name": "主播网红"},
    {"type_id": "340", "type_name": "日本素人"},
    {"type_id": "408", "type_name": "亚洲有码"},
    {"type_id": "409", "type_name": "亚洲无码"},
    {"type_id": "410", "type_name": "制服诱惑"},
    {"type_id": "411", "type_name": "强奸乱伦"},
    {"type_id": "412", "type_name": "巨乳美乳"},
    {"type_id": "413", "type_name": "AI换脸"},
    {"type_id": "414", "type_name": "中文字幕"},
    {"type_id": "415", "type_name": "角色扮演"},
    {"type_id": "416", "type_name": "日本女优"},
    {"type_id": "417", "type_name": "成人动漫"},
    {"type_id": "418", "type_name": "欧美激情"},
    {"type_id": "419", "type_name": "三级片"},
    {"type_id": "420", "type_name": "网曝视频"},
    {"type_id": "421", "type_name": "AV解说"},
    {"type_id": "422", "type_name": "国产传媒"},
    {"type_id": "423", "type_name": "主播直播"},
    {"type_id": "424", "type_name": "国产精品"},
    {"type_id": "425", "type_name": "国产探花"},
    {"type_id": "426", "type_name": "国产乱伦"},
    {"type_id": "427", "type_name": "国产丝袜"},
    {"type_id": "428", "type_name": "国产SM"},
    {"type_id": "429", "type_name": "国产人妻"},
    {"type_id": "430", "type_name": "自拍偷拍"},
    {"type_id": "431", "type_name": "同性恋"},
    {"type_id": "432", "type_name": "国产自拍"},
    {"type_id": "433", "type_name": "日本无码"},
    {"type_id": "434", "type_name": "日本有码"},
    {"type_id": "435", "type_name": "中文字幕"},
    {"type_id": "436", "type_name": "欧美精品"},
    {"type_id": "437", "type_name": "成人动漫"},
    {"type_id": "438", "type_name": "日本素人"},
    {"type_id": "439", "type_name": "高清名优"},
    {"type_id": "440", "type_name": "三级伦理"},
    {"type_id": "441", "type_name": "网红主播"},
    {"type_id": "442", "type_name": "映画传媒"},
    {"type_id": "443", "type_name": "人妻熟女"},
    {"type_id": "444", "type_name": "口爆颜射"},
    {"type_id": "446", "type_name": "SM调教"},
    {"type_id": "447", "type_name": "美乳巨乳"},
    {"type_id": "448", "type_name": "短视频"},
    {"type_id": "449", "type_name": "制服诱惑"},
    {"type_id": "450", "type_name": "女同性爱"},
    {"type_id": "451", "type_name": "AI换脸"},
    {"type_id": "452", "type_name": "多人群交"},
    {"type_id": "453", "type_name": "翹臀美尻"},
    {"type_id": "454", "type_name": "丝袜美腿"},
    {"type_id": "455", "type_name": "精选独家"},
    {"type_id": "456", "type_name": "貧乳小奶"},
    {"type_id": "457", "type_name": "探花系列"},
    {"type_id": "458", "type_name": "AV解说"},
    {"type_id": "459", "type_name": "福利姬"},
    {"type_id": "483", "type_name": "福利姬"},
    {"type_id": "485", "type_name": "日韩无码"},
    {"type_id": "486", "type_name": "国产主播"},
    {"type_id": "487", "type_name": "日韩精品"},
    {"type_id": "488", "type_name": "欧美劲爆"},
    {"type_id": "489", "type_name": "成人动漫"},
    {"type_id": "490", "type_name": "自拍偷拍"},
    {"type_id": "491", "type_name": "伦理影片"},
    {"type_id": "492", "type_name": "中文字幕"},
    {"type_id": "493", "type_name": "人妻系列"},
    {"type_id": "494", "type_name": "制服诱惑"},
    {"type_id": "495", "type_name": "强奸乱伦"},
    {"type_id": "496", "type_name": "AV明星"},
    {"type_id": "497", "type_name": "SM重味"},
    {"type_id": "498", "type_name": "巨乳尤物"},
    {"type_id": "499", "type_name": "颜射系列"},
    {"type_id": "500", "type_name": "口交视频"},
    {"type_id": "501", "type_name": "自慰系列"},
    {"type_id": "502", "type_name": "教师学生"},
    {"type_id": "503", "type_name": "群P换妻"},
    {"type_id": "504", "type_name": "AI换脸"},
    {"type_id": "505", "type_name": "AV解说"},
    {"type_id": "506", "type_name": "吃瓜黑料"},
    {"type_id": "507", "type_name": "酒店探花"},
    {"type_id": "508", "type_name": "直播裸聊"},
    {"type_id": "509", "type_name": "反差母狗"},
    {"type_id": "510", "type_name": "颜值正义"},
    {"type_id": "511", "type_name": "熟女少妇"},
    {"type_id": "512", "type_name": "人兽乱交"},
    {"type_id": "513", "type_name": "国产传媒"},
    {"type_id": "514", "type_name": "野战车震"},
    {"type_id": "515", "type_name": "SM调教"},
    {"type_id": "516", "type_name": "家庭乱伦"},
    {"type_id": "517", "type_name": "百合女同"},
    {"type_id": "518", "type_name": "学生空姐"},
    {"type_id": "519", "type_name": "撸管必看"},
    {"type_id": "520", "type_name": "偷情少妇"},
]


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.siteUrl = "https://xxkfcaa.xyz"
        self.rawSite = "https://xxkfcaa.xyz"
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
        """从HTML中解析视频列表 (mytpl模板, 封面bgimg属性, 标题<p>标签)"""
        vod_list = []
        pattern = r'<a[^>]*href="[^"]*vod-detail/id-(\d+)\.html"[^>]*>(.*?)</a>'
        for vid, content in re.findall(pattern, html, re.S):
            # 封面 (bgimg属性)
            cover_m = re.search(r'bgimg="([^"]+)"', content)
            if not cover_m:
                cover_m = re.search(r'data-(?:src|original)="([^"]+)"', content)
            cover = cover_m.group(1) if cover_m else ""
            # 标题 (<p>标签)
            title_m = re.search(r'<p[^>]*>(.*?)</p>', content, re.S)
            title = ""
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title:
                title_attr = re.search(r'title="([^"]+)"', content)
                alt_attr = re.search(r'alt="([^"]+)"', content)
                title = (title_attr.group(1) if title_attr else (alt_attr.group(1) if alt_attr else ""))
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
        # 首页为导航页无视频列表, 抓取首个分类页作为首页推荐
        html = self._fetch(self.siteUrl + "/vod-type/id-123-by-time-pg-1.html")
        result["list"] = self._parse_videos(html) if html else []
        return result

    # ==================== 2. categoryContent ====================
    def categoryContent(self, tid, page=1, *args):
        result = {}
        page = int(page)
        url = f"{self.siteUrl}/vod-type/id-{tid}-by-time-pg-{page}.html"
        html = self._fetch(url)
        vod_list = self._parse_videos(html)
        # 分页 (站点分页链接可能由JS加载, 默认999页)
        pages = re.findall(r'/vod-type/id-' + re.escape(tid) + r'-by-time-pg-(\d+)\.html', html)
        max_page = max(int(p) for p in pages) if pages else 999
        result["page"] = page
        result["pagecount"] = max_page
        result["limit"] = 10
        result["total"] = max_page * 10
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
            dhtml = self._fetch(f"{self.siteUrl}/vod-detail/id-{vod_id}.html")
            if not dhtml:
                continue
            # 标题
            title_m = re.search(r'<title>(.*?)</title>', dhtml, re.S)
            vod_name = ""
            if title_m:
                vod_name = title_m.group(1).split('-')[0].strip()
            if not vod_name:
                p_m = re.search(r'<p[^>]*>(.*?)</p>', dhtml, re.S)
                if p_m:
                    vod_name = re.sub(r'<[^>]+>', '', p_m.group(1)).strip()
            if is_minor(vod_name):
                continue
            # 封面
            cover_m = re.search(r'bgimg="([^"]+)"', dhtml)
            if not cover_m:
                cover_m = re.search(r'data-(?:src|original)="([^"]+)"', dhtml)
            vod_pic = cover_m.group(1) if cover_m else ""
            # 播放页
            play_url = ""
            play_from = "ckplayer"
            phtml = self._fetch(f"{self.siteUrl}/vod-play/id-{vod_id}.html")
            if phtml:
                # 从ckplayer URL参数提取m3u8: player.php?url=ENCODED_M3U8
                ck_m = re.search(r'player\.php\?url=([^"\'&\s]+)', phtml)
                if ck_m:
                    play_url = urllib.parse.unquote(ck_m.group(1))
                # 兜底: 直接找m3u8
                if not play_url:
                    m3u8_m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', phtml)
                    if m3u8_m:
                        play_url = m3u8_m.group(1)
            if play_url and '$' not in play_url:
                play_url = f"第1集${play_url}"
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": self._abs_url(vod_pic),
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            })
        result["list"] = vod_list
        return result

    # ==================== 4. playerContent ====================
    def playerContent(self, flag, id, vipFlags=None, *args):
        result = {}
        play_url = id if id.startswith("http") else self._abs_url(id)
        result["parse"] = 0
        result["jx"] = 0
        result["url"] = play_url
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
        url = f"{self.siteUrl}/vod-search/wd-{key_enc}-by-time-pg-{page}.html"
        html = self._fetch(url)
        vod_list = self._parse_videos(html)
        result["page"] = page
        result["pagecount"] = 1
        result["limit"] = 10
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
        return "苹果影院 Spider loaded"

    def getName(self):
        return "苹果影院"

    def destroy(self):
        self._session = None
