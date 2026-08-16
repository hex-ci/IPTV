#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""北京联通 IPTV 频道列表维护脚本。

用法:
    python3 update_channels.py            # 拉基准对比，打印 新增/删除/地址漂移
    python3 update_channels.py --apply    # 用内置映射表重新生成 m3u（分组+排序+EPG/台标）

信息源变化时改下面 CONFIG；新增频道时在 MAPPING 里补映射。
"""

import re
import sys
import urllib.request

# ============ 可配置项 ============
TARGET = "beijing-unicom.m3u"
ISLC_URL = "https://raw.githubusercontent.com/islercn/BeiJing-Unicom-IPTV-List/refs/heads/master/iptv.m3u"
GIST_RAW = "https://gist.githubusercontent.com/sdhzdmzzl/93cf74947770066743fff7c7f4fc5820/raw"
GIST_COMMENTS_API = "https://api.github.com/gists/93cf74947770066743fff7c7f4fc5820/comments"
EPG_URL = "http://epg.51zmt.top:8000/e1.xml.gz"
LOGO_BASE = "http://epg.51zmt.top:8000/tb1/"

GROUP_ORDER = [
    "[4K]央视", "[4K]北京", "[4K]卫视", "[4K]数字付费",
    "[高清]央视", "[高清]北京", "[高清]卫视", "[高清]少儿",
    "[高清]教育", "[高清]数字付费", "[高清]购物", "[高清]IPTV专区",
    "[标清]卫视", "[标清]北京", "[标清]少儿", "[标清]教育",
    "[标清]数字付费",
    "[测试]",
]

# ============ 映射表: 组播地址 -> (分组, tvg-id, tvg-name, 台标路径) ============
# 台标路径相对 tb1/；空串=无。新增频道在此补一行。
M = {}

# [4K]央视
M["239.3.1.245:2000"] = ("[4K]央视", "106", "CCTV4K", "CCTV/CCTV4k.png")
M["239.3.1.183:8001"] = ("[4K]央视", "1864", "CCTV16", "CCTV/CCTV16.png")

# [4K]北京
M["239.3.1.22:8001"]  = ("[4K]北京", "30", "北京卫视", "ws/beijing.png")
M["239.3.1.118:8001"] = ("[4K]北京", "30", "北京卫视", "ws/beijing.png")
M["239.3.1.249:8001"] = ("[4K]北京", "", "", "")
M["239.3.1.120:8000"] = ("[4K]北京", "1178", "BTV体育", "sheng/BTV体育.png")
M["239.3.1.121:8000"] = ("[4K]北京", "1178", "BTV体育", "sheng/BTV体育.png")

# [4K]卫视
for a, tid, tn, lg in [
    ("239.3.1.112:3002", "27", "湖南卫视", "ws/hunan.png"),
    ("239.3.1.203:2000", "33", "广东卫视", "ws/guangdong.png"),
    ("239.3.1.113:3003", "29", "江苏卫视", "ws/jiangsu.png"),
    ("239.3.1.202:2000", "34", "深圳卫视", "ws/shenzhen.png"),
    ("239.3.1.119:3006", "31", "东方卫视", "ws/dongfang.png"),
    ("239.3.1.114:3004", "28", "浙江卫视", "ws/zhejiang.png"),
    ("239.3.1.144:3005", "38", "山东卫视", "ws/shandong.png"),
    ("239.3.1.131:3001", "56", "四川卫视", "ws/sichuan.png"),
]:
    M[a] = ("[4K]卫视", tid, tn, lg)

# [4K]数字付费
M["239.3.1.107:8001"] = ("[4K]数字付费", "1642", "求索记录", "")
M["239.3.1.236:2000"] = ("[4K]数字付费", "", "", "")

# [高清]央视
for a, tid, tn, lg in [
    ("239.3.1.129:8008", "1", "CCTV1", "CCTV/CCTV1.png"),
    ("239.3.1.60:8084", "2", "CCTV2", "CCTV/CCTV2.png"),
    ("239.3.1.172:8001", "3", "CCTV3", "CCTV/CCTV3.png"),
    ("239.3.1.105:8092", "4", "CCTV4", "CCTV/CCTV4.png"),
    ("239.3.1.173:8001", "5", "CCTV5", "CCTV/CCTV5.png"),
    ("239.3.1.130:8004", "6", "CCTV5+", "CCTV/CCTV5+.png"),
    ("239.3.1.174:8001", "7", "CCTV6", "CCTV/CCTV6.png"),
    ("239.3.1.61:8104", "8", "CCTV7", "CCTV/CCTV7.png"),
    ("239.3.1.175:8001", "9", "CCTV8", "CCTV/CCTV8.png"),
    ("239.3.1.62:8112", "10", "CCTV9", "CCTV/CCTV9.png"),
    ("239.3.1.63:8116", "11", "CCTV10", "CCTV/CCTV10.png"),
    ("239.3.1.152:8120", "12", "CCTV11", "CCTV/CCTV11.png"),
    ("239.3.1.64:8124", "13", "CCTV12", "CCTV/CCTV12.png"),
    ("239.3.1.124:8128", "14", "CCTV13", "CCTV/CCTV13.png"),
    ("239.3.1.65:8132", "15", "CCTV14", "CCTV/CCTV14.png"),
    ("239.3.1.153:8136", "16", "CCTV15", "CCTV/CCTV15.png"),
    ("239.3.1.184:8001", "1864", "CCTV16", "CCTV/CCTV16.png"),
    ("239.3.1.151:8144", "17", "CCTV17", "CCTV/CCTV17.png"),
    ("239.3.1.213:4220", "22", "CCTV4EUO", "CCTV/CCTV4EUO.png"),
    ("239.3.1.214:4220", "23", "CCTV4AME", "CCTV/CCTV4AME.png"),
]:
    M[a] = ("[高清]央视", tid, tn, lg)
for a in ["239.3.1.215:4220", "239.3.1.216:4220", "239.3.1.217:4220",
          "239.3.1.218:4220", "239.3.1.219:4220", "239.3.1.220:4220"]:
    M[a] = ("[高清]央视", "20", "CGTN", "CCTV/cgtn.png")

# [高清]北京
for a, tid, tn, lg in [
    ("239.3.1.241:8000", "30", "北京卫视", "ws/beijing.png"),
    ("239.3.1.242:8000", "1174", "BTV文艺", "sheng/BTV文艺.png"),
    ("239.3.1.115:8000", "1173", "北京纪实", "sheng/BTV科教.png"),
    ("239.3.1.158:8000", "1176", "BTV影视", "sheng/BTV影视.png"),
    ("239.3.1.116:8000", "1177", "BTV财经", "sheng/BTV财经.png"),
    ("239.3.1.243:8000", "1178", "BTV体育", "sheng/BTV体育.png"),
    ("239.3.1.117:8000", "1179", "BTV生活", "sheng/BTV生活.png"),
    ("239.3.1.159:8000", "1181", "BTV新闻", "sheng/BTV新闻.png"),
    ("239.3.1.235:8000", "", "", ""),
]:
    M[a] = ("[高清]北京", tid, tn, lg)
for a in ["239.3.1.163:8001", "239.3.1.154:8001", "239.3.1.96:8001",
          "239.3.1.221:8001", "239.3.1.59:8001", "239.3.1.23:8001"]:
    M[a] = ("[高清]北京", "", "", "")

# [高清]卫视
for a, tid, tn, lg in [
    ("239.3.1.132:8012", "27", "湖南卫视", "ws/hunan.png"),
    ("239.3.1.135:8028", "29", "江苏卫视", "ws/jiangsu.png"),
    ("239.3.1.136:8032", "31", "东方卫视", "ws/dongfang.png"),
    ("239.3.1.137:8036", "28", "浙江卫视", "ws/zhejiang.png"),
    ("239.3.1.138:8044", "48", "湖北卫视", "ws/hubei.png"),
    ("239.3.1.141:1234", "39", "天津卫视", "ws/tianjin.png"),
    ("239.3.1.209:8052", "38", "山东卫视", "ws/shandong.png"),
    ("239.3.1.210:8056", "36", "辽宁卫视", "ws/liaoning.png"),
    ("239.3.1.211:8064", "32", "安徽卫视", "ws/anhui.png"),
    ("239.3.1.133:8016", "46", "黑龙江卫视", "ws/heilongjiang.png"),
    ("239.3.1.149:8076", "44", "贵州卫视", "ws/guizhou.png"),
    ("239.3.1.156:8148", "41", "东南卫视", "ws/dongnan.png"),
    ("239.3.1.122:8160", "40", "重庆卫视", "ws/chongqing.png"),
    ("239.3.1.123:8164", "50", "江西卫视", "ws/jiangxi.png"),
    ("239.3.1.50:8184", "47", "河南卫视", "ws/henan.png"),
    ("239.3.1.201:8180", "42", "甘肃卫视", "ws/gansu.png"),
    ("239.3.1.166:8188", "71", "西藏卫视", "ws/xizang.png"),
    ("239.3.1.167:8192", "57", "新疆卫视", "ws/xinjiang.png"),
    ("239.3.1.169:8212", "53", "宁夏卫视", "ws/ningxia.png"),
    ("239.3.1.142:8048", "33", "广东卫视", "ws/guangdong.png"),
    ("239.3.1.148:8072", "45", "河北卫视", "ws/hebei.png"),
    ("239.3.1.134:8020", "34", "深圳卫视", "ws/shenzhen.png"),
    ("239.3.1.240:8172", "51", "吉林卫视", "ws/jilin.png"),
    ("239.3.1.168:8196", "61", "兵团卫视", "ws/bingtuan.png"),
]:
    M[a] = ("[高清]卫视", tid, tn, lg)

# [高清]少儿 / [高清]教育
M["239.3.1.189:8000"] = ("[高清]少儿", "67", "卡酷动画", "qt/kaku.png")
M["239.3.1.57:8152"]  = ("[高清]教育", "73", "中国教育1台", "qt/中国教育1台.png")

# [高清]数字付费
for a, tid, tn, lg in [
    ("239.3.1.212:8060", "", "", ""),
    ("239.3.1.58:8156", "1324", "金鹰纪实", "ws/jinyingjishi.png"),
    ("239.3.1.188:8001", "1293", "中国交通频道", ""),
    ("239.3.1.24:8001", "1671", "证券资讯", ""),
    ("239.3.1.164:8001", "1684", "快乐垂钓", "qt/KUAILECHUIDIAO.jpg"),
    ("239.3.1.165:8001", "", "", ""),
    ("239.3.1.66:8068", "", "", ""),
    ("239.3.1.25:8001", "", "", ""),
    ("239.3.1.157:8176", "", "", ""),
    ("239.3.1.106:8001", "1643", "CHC动作电影", ""),
    ("239.3.1.108:8001", "", "", ""),
    ("239.3.1.109:8001", "1697", "环球旅游", ""),
]:
    M[a] = ("[高清]数字付费", tid, tn, lg)

# [高清]购物
for a in ["239.3.1.179:8001", "239.3.1.160:8001", "239.3.1.222:8001",
          "239.3.1.223:8001", "239.3.1.186:8001", "239.3.1.185:8001",
          "239.3.1.180:8001", "239.3.1.190:8001", "239.3.1.181:8001",
          "239.3.1.191:8001", "239.3.1.178:8001"]:
    M[a] = ("[高清]购物", "", "", "")

# [高清]IPTV专区
for a in ["239.3.1.102:8001", "239.3.1.238:8001", "239.3.1.95:8001",
          "239.3.1.250:8001", "239.3.1.100:8001",
          "239.3.1.125:8001", "239.3.1.126:8001", "239.3.1.127:8001",
          "239.3.1.128:8001", "239.3.1.193:8012", "239.3.1.194:9020",
          "239.3.1.195:9024", "239.3.1.196:9012", "239.3.1.199:9000",
          "239.3.1.67:4120", "239.3.1.68:4120", "239.3.1.69:4120",
          "239.3.1.70:4120", "239.3.1.71:4120", "239.3.1.72:4120",
          "239.3.1.73:4120", "239.3.1.74:4120", "239.3.1.75:4120",
          "239.3.1.76:4120", "239.3.1.77:4120", "239.3.1.78:4120",
          "239.3.1.79:4120", "239.3.1.80:4120", "239.3.1.81:4120",
          "239.3.1.82:4120", "239.3.1.83:4120", "239.3.1.84:4120",
          "239.3.1.85:4120", "239.3.1.86:4120", "239.3.1.87:4120",
          "239.3.1.88:4120", "239.3.1.89:4120", "239.3.1.90:4120",
          "239.3.1.91:4120", "239.3.1.92:4120", "239.3.1.93:4120",
          "239.3.1.94:4120", "239.3.1.198:9004", "239.3.1.200:9008",
          "239.3.1.197:9016", "239.3.1.201:8072", "239.3.1.237:4120"]:
    M[a] = ("[高清]IPTV专区", "", "", "")
M["239.3.1.77:4120"] = ("[高清]IPTV专区", "1679", "国学", "qt/SHUOWENJIEZI.jpg")

# [标清]卫视
for a, tid, tn, lg in [
    ("239.3.1.29:8288", "56", "四川卫视", "ws/sichuan.png"),
    ("239.3.1.39:8300", "43", "广西卫视", "ws/guangxi.png"),
    ("239.3.1.41:8140", "55", "陕西卫视", "ws/shanxi.png"),
    ("239.3.1.42:8172", "54", "山西卫视", "ws/shanxi_.png"),
    ("239.3.1.43:8176", "52", "内蒙古卫视", "ws/neimeng.png"),
    ("239.3.1.44:8184", "59", "青海卫视", "ws/qinghai.png"),
    ("239.3.1.45:8304", "37", "旅游卫视", "ws/lvyou.png"),
    ("239.3.1.155:4120", "72", "三沙卫视", "ws/sansha.png"),
    ("239.3.1.26:8108", "58", "云南卫视", "ws/yunnan.png"),
    ("239.3.1.143:4120", "68", "厦门卫视", "ws/xiamen.png"),
    ("239.3.1.161:8001", "1995", "大湾区卫视", "ws/nanfang.png"),
]:
    M[a] = ("[标清]卫视", tid, tn, lg)

# [标清]北京
for a, tid, tn, lg in [
    ("239.3.1.225:8000", "30", "北京卫视", "ws/beijing.png"),
    ("239.3.1.226:8000", "1174", "BTV文艺", "sheng/BTV文艺.png"),
    ("239.3.1.227:8000", "1173", "北京纪实", "sheng/BTV科教.png"),
    ("239.3.1.228:8000", "1176", "BTV影视", "sheng/BTV影视.png"),
    ("239.3.1.229:8000", "1177", "BTV财经", "sheng/BTV财经.png"),
    ("239.3.1.231:8000", "1179", "BTV生活", "sheng/BTV生活.png"),
    ("239.3.1.233:8000", "1181", "BTV新闻", "sheng/BTV新闻.png"),
    ("239.3.1.230:8000", "1178", "BTV体育", "sheng/BTV体育.png"),
    ("239.3.1.187:8001", "", "", ""),
]:
    M[a] = ("[标清]北京", tid, tn, lg)

# [标清]少儿
M["239.3.1.234:8000"] = ("[标清]少儿", "67", "卡酷动画", "qt/kaku.png")
M["239.3.1.51:9252"]  = ("[标清]少儿", "69", "金鹰卡通", "qt/jinyingkatong.png")
M["239.3.1.147:9268"] = ("[标清]少儿", "1434", "嘉佳卡通", "qt/jiajiakt.png")

# [标清]教育
for a, tid, tn, lg in [
    ("239.3.1.54:4120", "74", "中国教育2台", "qt/中国教育2台.png"),
    ("239.3.1.55:4120", "75", "中国教育3台", "qt/中国教育3台.png"),
    ("239.3.1.56:4120", "1860", "中国教育4台", "qt/中国教育4台.png"),
    ("239.3.1.52:4120", "", "", ""),
]:
    M[a] = ("[标清]教育", tid, tn, lg)

# [标清]数字付费
M["239.3.1.53:9136"] = ("[标清]数字付费", "1712", "财富天下", "qt/财富天下.png")

# [测试]
for a in ["239.3.1.139:8001", "239.3.1.140:8001", "239.3.1.103:8001",
          "239.3.1.104:8001", "239.3.1.247:2000", "239.3.1.248:2000",
          "239.3.1.253:8001"]:
    M[a] = ("[测试]", "", "", "")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def parse_m3u(text, url_regex):
    """解析 m3u 文本 -> {addr: (name, chno)}。url_regex 提取 ip:port。"""
    out = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#EXTINF"):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            url = lines[j].strip() if j < len(lines) else ""
            m = re.search(url_regex, url)
            if m:
                name = ln.rsplit(",", 1)[-1].strip()
                chno = re.search(r"\[(\d+)\]", name)
                out[m.group(1)] = (name, chno.group(1) if chno else "")
            i = j + 1
        else:
            i += 1
    return out


def parse_my(path):
    data = open(path, encoding="utf-8").read()
    return parse_m3u(data, r"/rtp/([\d.]+:\d+)")


def diff():
    """拉基准对比现有文件，打印差异报告。"""
    islc_text = fetch(ISLC_URL)
    gist_text = fetch(GIST_RAW)

    islc = parse_m3u(islc_text, r"/rtp/([\d.]+:\d+)")
    gist = parse_m3u(gist_text, r"rtp://([\d.]+:\d+)")
    bench = set(islc) | set(gist)
    mine = parse_my(TARGET)
    my_addr = set(mine)

    to_add = sorted(bench - my_addr)
    to_del = sorted(my_addr - bench)

    print(f"现有: {len(mine)}  基准并集: {len(bench)} (islc {len(islc)} + gist {len(gist)})")
    print(f"\n== 新增(基准有、本地无) {len(to_add)} ==")
    for a in to_add:
        src = islc.get(a) or gist.get(a)
        print(f"  {a:18s} {src[0] if src else '?'}")

    print(f"\n== 删除(本地有、基准无) {len(to_del)} ==")
    for a in to_del:
        print(f"  {a:18s} {mine[a][0]}")


def generate():
    """按映射表重新生成 m3u。"""
    data = open(TARGET, encoding="utf-8").read()
    lines = data.splitlines()
    prefix = None
    for l in lines:
        m = re.search(r"(https?://[^/]+/rtp/)", l)
        if m:
            prefix = m.group(1)
            break
    if not prefix:
        print("无法识别 URL 前缀"); sys.exit(1)

    channels, order = {}, []
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#EXTINF"):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            url = lines[j].strip() if j < len(lines) else ""
            m = re.search(r"/rtp/([\d.]+:\d+)", url)
            addr = m.group(1) if m else None
            name = ln.rsplit(",", 1)[-1]
            chno = re.search(r"\[(\d+)\]", name)
            if addr:
                channels[addr] = (name, chno.group(1) if chno else "")
                order.append(addr)
            i = j + 1
        else:
            i += 1

    missing = [a for a in order if a not in M]
    if missing:
        print("!! 映射表缺少这些地址，请先补 M:\n  " + "\n  ".join(f"{a} {channels[a][0]}" for a in missing))
        sys.exit(1)

    def sort_key(addr):
        gi = GROUP_ORDER.index(M[addr][0])
        chno = channels[addr][1]
        n = int(chno) if chno.isdigit() else 999999
        if addr == "239.3.1.130:8004":   # CCTV5+ 紧跟 CCTV5
            n = 5.5
        if addr == "239.3.1.139:8001":   # VBR测试-1 紧跟 VBR测试-2
            n = 502.5
        return (gi, n)

    out = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    for a in sorted(order, key=sort_key):
        g, tid, tname, logo = M[a]
        name = channels[a][0]
        logo_url = (LOGO_BASE + logo) if logo else ""
        out.append(f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{tname}" tvg-logo="{logo_url}" group-title="{g}",{name}')
        out.append(f"{prefix}{a.split(':')[0]}:{a.split(':')[1]}")
        out.append("")

    open(TARGET, "w", encoding="utf-8").write("\n".join(out).rstrip("\n") + "\n")
    print(f"已生成 {len(order)} 个频道")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        generate()
    else:
        diff()