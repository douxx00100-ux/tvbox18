# -*- coding: utf-8 -*-
# 高清AV 四壳通用Python Spider
# 站点: https://www.gaoqingav.one
# 架构: 苹果CMS变体 + 直链播放页(无详情页) + player_aaaa(encrypt=0)
# 播放: m3u8直链

import re
import json
import html as html_mod
import urllib.parse

try:
    from base.spider import Spider
except Exception:
    class Spider:
        def __init__(self):
            self.extend = {}

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.rawSite = "https://www.gaoqingav.one"
        self.siteUrl = self.rawSite
        self.HOST = self.siteUrl
        self._session = None
        self._use_curl_cffi = None

    def init(self, extend=""):
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else extend
                if ext.get("proxy"):
                    self.siteUrl = ext["proxy"]
                    self.HOST = self.siteUrl
                if ext.get("siteUrl"):
                    self.siteUrl = ext["siteUrl"]
                    self.HOST = self.siteUrl
                if ext.get("direct"):
                    self.siteUrl = self.rawSite
                    self.HOST = self.rawSite
            except Exception:
                pass

    def _get_session(self):
        if self._use_curl_cffi is None:
            try:
                from curl_cffi import requests as cffi_requests
                self._session = cffi_requests.Session(impersonate="chrome131")
                self._use_curl_cffi = True
            except Exception:
                self._use_curl_cffi = False
        return self._session

    def _req(self, url):
        sess = self._get_session()
        if self._use_curl_cffi and sess:
            try:
                r = sess.get(url, timeout=15)
                return r.text
            except Exception:
                return ""
        else:
            import urllib.request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    charset = "utf-8"
                    ct = resp.headers.get("Content-Type", "")
                    if "charset=" in ct:
                        charset = ct.split("charset=")[-1].split(";")[0].strip()
                    return data.decode(charset, errors="ignore")
            except Exception:
                return ""

    def _parse_list(self, html):
        """解析视频列表 - .video-list ul li"""
        result = []
        # 匹配 li 中的播放链接和封面
        pattern = re.compile(
            r'<li>.*?<a[^>]*href="(/aa/index\.php/vod/play/id/(\d+)/sid/\d+/nid/\d+\.html)"[^>]*>.*?'
            r'<img[^>]*data-original="([^"]*)".*?</li>',
            re.S
        )
        seen = set()
        for m in pattern.finditer(html):
            vod_id = m.group(2)
            if vod_id in seen:
                continue
            seen.add(vod_id)
            vod_pic = m.group(3)
            if vod_pic.startswith("//"):
                vod_pic = "https:" + vod_pic
            # 标题在 h3.video-title 中: <a href="play_url"></a><a><text>标题</text></a>
            title_pattern = re.compile(
                r'/aa/index\.php/vod/play/id/' + re.escape(vod_id) + r'/sid/\d+/nid/\d+\.html"[^>]*></a><a><text>([^<]+)</text>',
                re.S
            )
            title_m = title_pattern.search(html)
            vod_name = html_mod.unescape(title_m.group(1).strip()) if title_m else vod_id
            result.append({
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": "",
            })
        return result

    def _get_total(self, html, type_id=None):
        """获取总页数"""
        if type_id:
            pages = re.findall(r'/aa/index\.php/vod/type/id/' + re.escape(type_id) + r'/page/(\d+)\.html', html)
        else:
            pages = re.findall(r'/page/(\d+)', html)
        if pages:
            max_page = max(int(p) for p in pages)
            return max_page * 20
        return 0

    def homeContent(self, *args):
        result = {}
        classes = self._get_classes()
        result["class"] = classes
        html = self._req(self.siteUrl + "/aa/?id=yng")
        videos = self._parse_list(html)
        result["list"] = videos
        filters = {}
        for c in classes:
            filters[c["type_id"]] = []
        result["filters"] = filters
        return result

    def _get_classes(self):
        html = self._req(self.siteUrl + "/aa/?id=yng")
        classes = []
        seen = set()
        pattern = re.compile(r'<a[^>]*href="/aa/index\.php/vod/type/id/(\d+)\.html"[^>]*>\s*<text>([^<]+)</text>', re.S)
        for m in pattern.finditer(html):
            tid = m.group(1)
            tname = html_mod.unescape(m.group(2).strip())
            if tname and tid not in seen and len(tname) < 15 and tname != "更多":
                # 铁律13: 跳过未成年相关分类
                minor_keywords = ['萝莉', '幼女', '少女', '童', 'teen', 'loli', 'schoolgirl', '豆蔻', '玉蕊', '碧玉', '稚子']
                if any(kw.lower() in tname.lower() for kw in minor_keywords):
                    continue
                seen.add(tid)
                classes.append({"type_id": tid, "type_name": tname})
        return classes

    def categoryContent(self, tid, pg, *args):
        if not pg or pg == "1":
            url = self.siteUrl + f"/aa/index.php/vod/type/id/{tid}.html"
        else:
            url = self.siteUrl + f"/aa/index.php/vod/type/id/{tid}/page/{pg}.html"
        html = self._req(url)
        videos = self._parse_list(html)
        total = self._get_total(html, tid)
        pagecount = (total + 19) // 20 if total > 0 else 1
        return {
            "page": int(pg) if pg else 1,
            "pagecount": pagecount,
            "limit": 20,
            "total": total,
            "list": videos,
        }

    def _extract_player_aaaa(self, html):
        """从播放页提取player_aaaa（处理嵌套大括号）"""
        m = re.search(r'var player_aaaa\s*=\s*', html)
        if not m:
            return None
        start = m.end()
        depth = 0
        end = start
        for i in range(start, min(start + 8000, len(html))):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(html[start:end])
        except Exception:
            return None

    def detailContent(self, array):
        if not array:
            return {"list": []}
        vod_id = str(array[0])
        # 此站无详情页(500)，从播放页取元数据
        play_url = self.siteUrl + f"/aa/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self._req(play_url)
        if not html:
            return {"list": []}

        data = self._extract_player_aaaa(html)
        vod_name = ""
        vod_pic = ""
        vod_content = ""
        if data:
            vod_data = data.get("vod_data", {})
            vod_name = html_mod.unescape(vod_data.get("vod_name", ""))
            vod_content = html_mod.unescape(vod_data.get("vod_content", ""))
            if not vod_content:
                actor = vod_data.get("vod_actor", "")
                director = vod_data.get("vod_director", "")
                vclass = vod_data.get("vod_class", "")
                parts = [p for p in [f"分类:{vclass}", f"导演:{director}", f"演员:{actor}"] if p and ":" not in p.split(":")[1]]
                vod_content = " ".join(parts)

        # 从页面提取封面
        pic_m = re.search(r'data-original="([^"]+)"', html)
        if pic_m:
            vod_pic = pic_m.group(1)
            if vod_pic.startswith("//"):
                vod_pic = "https:" + vod_pic

        # 构建播放源和剧集
        vod_play_from = ""
        vod_play_url = ""
        play_pattern = re.compile(r'/aa/index\.php/vod/play/id/' + re.escape(vod_id) + r'/sid/(\d+)/nid/(\d+)\.html')
        play_links = {}
        for m in play_pattern.finditer(html):
            sid = m.group(1)
            nid = m.group(2)
            if sid not in play_links:
                play_links[sid] = set()
            play_links[sid].add(nid)

        if play_links:
            sources = []
            urls = []
            for sid in sorted(play_links.keys(), key=int):
                eps = sorted(play_links[sid], key=int)
                ep_list = []
                for nid in eps:
                    ep_list.append(f"第{nid}集${self.siteUrl}/aa/index.php/vod/play/id/{vod_id}/sid/{sid}/nid/{nid}.html")
                sources.append(f"源{sid}")
                urls.append("#".join(ep_list))
            vod_play_from = "$$$".join(sources)
            vod_play_url = "$$$".join(urls)
        else:
            vod_play_from = "默认"
            vod_play_url = f"第1集${play_url}"

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_content": vod_content,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}
        play_url = id if id.startswith("http") else self.siteUrl + id
        html = self._req(play_url)
        if not html:
            return {"parse": 0, "jx": 0, "url": "", "header": {}}

        video_url = ""
        data = self._extract_player_aaaa(html)
        if data:
            video_url = data.get("url", "")
            # encrypt=0 直出，encrypt=1 需URL解码
            if data.get("encrypt") == 1 and video_url:
                video_url = urllib.parse.unquote(video_url)

        if not video_url:
            m3u8_m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m3u8_m:
                video_url = m3u8_m.group(1)

        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": self.rawSite + "/",
            "Origin": self.rawSite,
        }

        return {
            "parse": 0,
            "jx": 0,
            "url": video_url,
            "header": header,
        }

    def searchContent(self, wd, pg, *args):
        page = int(pg) if pg else 1
        url = self.siteUrl + f"/aa/index.php/vod/search/page/{page}/wd/{urllib.parse.quote(wd)}.html"
        html = self._req(url)
        videos = self._parse_list(html)
        total = self._get_total(html)
        pagecount = (total + 19) // 20 if total > 0 else 1
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": total,
            "list": videos,
        }

    def getDependence(self, *args):
        return ""

    def localProxy(self, *args):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        return url.endswith(".m3u8") or url.endswith(".mp4")

    def manualVideoCheck(self):
        return False

    def getName(self):
        return "高清AV"

    def getApp(self):
        return "高清AV"
