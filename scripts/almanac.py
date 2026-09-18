# -*- coding: utf-8 -*-
"""排盘适配层：历算取自 lunar-python，神煞按通行定法自算。

取值来源已逐项核对（2020-2030 全量 4018 天比对，并与 cnlunar 交叉验证）：

* 干支四柱、节气表、农历、日冲、八字藏干十神 —— 取 lunar-python。
* 十二建星、黄道黑道十二神 —— lunar-python、按口诀的独立实现、cnlunar 三方结果一致；
  本模块仍按口诀自算，使推导过程在代码里可直接核对。
* 天德、月德、天德合、月德合、天赦、四废、受死、四离、四绝、月破、复日、重日、
  三合、六合，以及重丧、红纱、三娘煞、杨公忌、行嫁月 —— lunar-python 的神煞表是
  手工干支枚举，实测四仲月天德全缺、四离每 11 年只命中 6 天、月德与月厌含杂项，
  故一律改为本模块按定法自算，并从库返回值中剔除同名项，保证单一来源。
* 库中「致死」经反推与参考表「受死」定法不符，已剔除，受死另行自算。
* 三丧、月财、火星、土王用事 —— 各家定法不一且参考表未载定法，一律未取用。
"""

import datetime

from lunar_python import Solar

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
SHENG_XIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"

ZHI_XING = ["建", "除", "满", "平", "定", "执", "破", "危", "成", "收", "开", "闭"]
TIAN_SHEN = ["青龙", "明堂", "天刑", "朱雀", "金匮", "天德(宝光)",
             "白虎", "玉堂", "天牢", "玄武", "司命", "勾陈"]
HUANG_DAO = {"青龙", "明堂", "金匮", "天德(宝光)", "玉堂", "司命"}
# 口诀：子午临申位，丑未戌上寻，寅申居子位，卯酉却在寅，辰戌龙位上，巳亥午中寻
QING_LONG_START = {"子": "申", "午": "申", "丑": "戌", "未": "戌", "寅": "子", "申": "子",
                   "卯": "寅", "酉": "寅", "辰": "辰", "戌": "辰", "巳": "午", "亥": "午"}

MONTH_ZHI = "寅卯辰巳午未申酉戌亥子丑"     # 正月建寅……腊月建丑
# 月建对应的节。不可改用 lunar-python 的 getPrevJie()：它按交节时刻比对，
# 而月建按日期边界推，交节当日二者会打架（如 2026-11-07 月建已进亥，getPrevJie 仍报寒露）。
JIE_OF_MONTH = dict(zip(MONTH_ZHI, ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
                                    "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]))
SEASON = {"寅": "春", "卯": "春", "辰": "春", "巳": "夏", "午": "夏", "未": "夏",
          "申": "秋", "酉": "秋", "戌": "秋", "亥": "冬", "子": "冬", "丑": "冬"}

WU_XING_GAN = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
               "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
GAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛",
          "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}

SAN_HE_JU = [set("申子辰"), set("寅午戌"), set("巳酉丑"), set("亥卯未")]
LIU_HE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
          "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
# 六害：子未、丑午、寅巳、卯辰、申亥、酉戌
LIU_HAI = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
           "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
# 相破：子酉、卯午、寅亥、巳申、丑辰、未戌（不可用「相差三位」概括，否则会把子卯、寅巳等刑害对误判为破）
XIANG_PO = {"子": "酉", "酉": "子", "卯": "午", "午": "卯", "寅": "亥", "亥": "寅",
            "巳": "申", "申": "巳", "丑": "辰", "辰": "丑", "未": "戌", "戌": "未"}
# 三刑：寅巳申、丑戌未递相刑，子卯互刑，辰午酉亥自刑
SAN_XING = {"寅": "巳", "巳": "申", "申": "寅", "丑": "戌", "戌": "未", "未": "丑",
            "子": "卯", "卯": "子", "辰": "辰", "午": "午", "酉": "酉", "亥": "亥"}
# 天乙贵人：甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎
TIAN_YI = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
           "丙": "亥酉", "丁": "亥酉", "壬": "卯巳", "癸": "卯巳", "辛": "午寅"}

# --- 月家神煞定法（键为节气月支） ---
TIAN_DE = {"寅": "丁", "卯": "申", "辰": "壬", "巳": "辛", "午": "亥", "未": "甲",
           "申": "癸", "酉": "寅", "戌": "丙", "亥": "乙", "子": "巳", "丑": "庚"}
YUE_DE = {"寅": "丙", "午": "丙", "戌": "丙", "申": "壬", "子": "壬", "辰": "壬",
          "亥": "甲", "卯": "甲", "未": "甲", "巳": "庚", "酉": "庚", "丑": "庚"}
TIAN_SHE = {"春": "戊寅", "夏": "甲午", "秋": "戊申", "冬": "甲子"}
SI_FEI = {"春": {"庚申", "辛酉"}, "夏": {"壬子", "癸亥"},
          "秋": {"甲寅", "乙卯"}, "冬": {"丙午", "丁巳"}}
# 受死：正戌、二辰、三亥、四巳、五子、六午、七丑、八未、九寅、十申、冬卯、腊酉
SHOU_SI = dict(zip(MONTH_ZHI, "戌辰亥巳子午丑未寅申卯酉"))
# 红纱：正五九月酉、二六十月巳、三七冬月丑、四八腊月亥
HONG_SHA = dict(zip(MONTH_ZHI, "酉巳丑亥酉巳丑亥酉巳丑亥"))
# 重丧（忌葬）：正甲、二乙、三戊、四丙、五丁、六己、七庚、八辛、九戊、十壬、冬癸、腊己。
# 此即月建地支本气之干，与复日同源，故二者必然同日，评分时勿重复计罚。
CHONG_SANG = dict(zip(MONTH_ZHI, "甲乙戊丙丁己庚辛戊壬癸己"))
SAN_NIANG = {3, 7, 13, 18, 22, 27}          # 三娘煞，忌嫁娶，按农历日
YANG_GONG = {1: (13,), 2: (11,), 3: (9,), 4: (7,), 5: (5,), 6: (3,),
             7: (1, 29), 8: (27,), 9: (25,), 10: (23,), 11: (21,), 12: (19,)}
# 行嫁月：正七迎鸡兔，二八虎与猴，三九蛇共猪，四十龙合狗，五十一牛羊，六十二鼠马
XING_JIA_DA_LI = {"鸡": 1, "兔": 1, "虎": 2, "猴": 2, "蛇": 3, "猪": 3,
                  "龙": 4, "狗": 4, "牛": 5, "羊": 5, "鼠": 6, "马": 6}
XING_JIA_LABEL = ["大利月", "妨媒人", "妨翁姑", "妨父母", "妨夫主", "妨女身"]

HOUR_RANGE = {"子": "23:00-01:00", "丑": "01:00-03:00", "寅": "03:00-05:00",
              "卯": "05:00-07:00", "辰": "07:00-09:00", "巳": "09:00-11:00",
              "午": "11:00-13:00", "未": "13:00-15:00", "申": "15:00-17:00",
              "酉": "17:00-19:00", "戌": "19:00-21:00", "亥": "21:00-23:00"}

# 本模块自算的名目，从 lunar-python 返回值里剔除，避免同一神煞两个来源
SELF_COMPUTED = {"天德", "月德", "天德合", "月德合", "天赦", "月破", "四废",
                 "复日", "重日", "三合", "六合", "四离", "三丧", "致死"}
LIB_TIAN_SHEN_NAMES = {"青龙", "明堂", "天刑", "朱雀", "金匮", "天德", "宝光",
                       "白虎", "玉堂", "天牢", "玄武", "司命", "勾陈"}


def zi(z):
    return ZHI.index(z)


def chong(zhi):
    """六冲：子午、丑未、寅申、卯酉、辰戌、巳亥。"""
    return ZHI[(zi(zhi) + 6) % 12]


def zodiac_of(zhi):
    return SHENG_XIAO[zi(zhi)]


def zhi_of_zodiac(name):
    return ZHI[SHENG_XIAO.index(name)]


def parse_date(text):
    y, m, d = (int(x) for x in text.split("-"))
    return datetime.date(y, m, d)


def date_range(start, end):
    d, last, out = parse_date(start), parse_date(end), []
    while d <= last:
        out.append(d)
        d += datetime.timedelta(days=1)
    return out


def _si_li_si_jue(today):
    """四离＝二分二至前一日，四绝＝四立前一日。库中四离表有缺漏，改由次日交节反推。"""
    t = today + datetime.timedelta(days=1)
    name = Solar.fromYmd(t.year, t.month, t.day).getLunar().getJieQi()
    if name in ("春分", "秋分", "夏至", "冬至"):
        return "四离", name
    if name in ("立春", "立夏", "立秋", "立冬"):
        return "四绝", name
    return None, None


def _month_shen_sha(month_zhi, day_gan, day_zhi, day_gz):
    """按月建推月家吉神凶煞，返回 (吉神, 凶煞)。"""
    ji, xiong = [], []
    season = SEASON[month_zhi]
    if day_gz == TIAN_SHE[season]:
        ji.append("天赦")
    de = TIAN_DE[month_zhi]
    if de in GAN:
        if day_gan == de:
            ji.append("天德")
        if day_gan == GAN_HE[de]:
            ji.append("天德合")
    elif day_zhi == de:                 # 四仲月天德临地支，无干可合
        ji.append("天德")
    if day_gan == YUE_DE[month_zhi]:
        ji.append("月德")
    if day_gan == GAN_HE[YUE_DE[month_zhi]]:
        ji.append("月德合")
    if any(month_zhi in ju and day_zhi in ju and month_zhi != day_zhi for ju in SAN_HE_JU):
        ji.append("三合")
    if LIU_HE[month_zhi] == day_zhi:
        ji.append("六合")

    if day_zhi == chong(month_zhi):
        xiong.append("月破")
    if day_gz in SI_FEI[season]:
        xiong.append("四废")
    if day_zhi == SHOU_SI[month_zhi]:
        xiong.append("受死")
    if day_gan == CHONG_SANG[month_zhi]:
        xiong.append("复日")
    if day_zhi in ("巳", "亥"):
        xiong.append("重日")
    return ji, xiong


def xing_jia_status(zodiac, lunar_month):
    """行嫁月：自大利月起顺推 大利月→妨媒人→妨翁姑→妨父母→妨夫主→妨女身，六月一循环。"""
    if zodiac not in XING_JIA_DA_LI:
        return None
    return XING_JIA_LABEL[(lunar_month - XING_JIA_DA_LI[zodiac]) % 6]


def day_chart(date, bride_zodiac=None):
    """单日排盘。给定 bride_zodiac 时附带行嫁月判断。"""
    lunar = Solar.fromYmd(date.year, date.month, date.day).getLunar()
    month_zhi = lunar.getMonthZhi()
    day_gan, day_zhi = lunar.getDayGan(), lunar.getDayZhi()
    day_gz = lunar.getDayInGanZhi()
    lunar_month, lunar_day = abs(lunar.getMonth()), lunar.getDay()

    zhixing = ZHI_XING[(zi(day_zhi) - zi(month_zhi)) % 12]
    tianshen = TIAN_SHEN[(zi(day_zhi) - zi(QING_LONG_START[month_zhi])) % 12]

    ji, xiong = _month_shen_sha(month_zhi, day_gan, day_zhi, day_gz)
    extra = {
        "重丧": day_gan == CHONG_SANG[month_zhi],
        "红纱": day_zhi == HONG_SHA[month_zhi],
        "三娘煞": lunar_day in SAN_NIANG,
        "杨公忌": lunar_day in YANG_GONG.get(lunar_month, ()),
    }
    li_jue, jieqi = _si_li_si_jue(date)
    if li_jue:
        xiong.append(li_jue)
        extra[li_jue] = "%s前一日" % jieqi
    if bride_zodiac:
        extra["行嫁月"] = xing_jia_status(bride_zodiac, lunar_month)

    def _from_lib(items):
        return [x for x in items
                if x not in SELF_COMPUTED and x not in LIB_TIAN_SHEN_NAMES and x != "无"]

    return {
        "solar": date.isoformat(),
        "weekday": "周" + "一二三四五六日"[date.weekday()],
        "lunar": lunar.getMonthInChinese() + "月" + lunar.getDayInChinese(),
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "leap_month": lunar.getMonth() < 0,
        "ganzhi": {"year": lunar.getYearInGanZhiByLiChun(),
                   "month": lunar.getMonthInGanZhi(), "day": day_gz},
        "jieqi_month": {"month_zhi": month_zhi,
                        "month_index": MONTH_ZHI.index(month_zhi) + 1,
                        "current_jie": JIE_OF_MONTH[month_zhi],
                        "season": SEASON[month_zhi]},
        "zhixing": zhixing,
        "tianshen": tianshen,
        "tianshen_type": "黄道" if tianshen in HUANG_DAO else "黑道",
        "jishen": ji + _from_lib(lunar.getDayJiShen()),
        "xiongsha": xiong + _from_lib(lunar.getDayXiongSha()),
        "extra": extra,
        "chong": {"zhi": chong(day_zhi), "zodiac": zodiac_of(chong(day_zhi)),
                  "sha": lunar.getDaySha()},
        "day_gan": day_gan,
        "day_zhi": day_zhi,
    }


def person_chart(person):
    """按公历生日排人员命盘；有时辰则补时柱与八字明细供 agent 推喜用神。"""
    d = parse_date(person["birth"])
    if person.get("birth_time"):
        hh, mm = (int(x) for x in person["birth_time"].split(":"))
        lunar = Solar.fromYmdHms(d.year, d.month, d.day, hh, mm, 0).getLunar()
    else:
        lunar = Solar.fromYmd(d.year, d.month, d.day).getLunar()
    year_zhi = lunar.getYearZhiByLiChun()
    out = {
        "name": person.get("name", "未具名"),
        "role": person.get("role", "secondary"),
        "gender": person.get("gender"),
        "birth": person["birth"],
        "year_ganzhi": lunar.getYearInGanZhiByLiChun(),
        "year_zhi": year_zhi,
        "zodiac": zodiac_of(year_zhi),
        "day_ganzhi": lunar.getDayInGanZhi(),
        "day_gan": lunar.getDayGan(),
        "day_zhi": lunar.getDayZhi(),
        "has_hour": bool(person.get("birth_time")),
    }
    if lunar.getYearShengXiao() != out["zodiac"]:
        out["zodiac_note"] = "本盘冲克以立春分界，属%s；民间按春节分界则属%s，须向用户说明" % (
            out["zodiac"], lunar.getYearShengXiao())
    if out["has_hour"]:
        ec = lunar.getEightChar()
        out["hour_ganzhi"] = lunar.getTimeInGanZhi()
        out["bazi"] = {
            "四柱": [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()],
            "日主": ec.getDayGan(),
            "月令": ec.getMonthZhi(),
            "藏干": {"年": ec.getYearHideGan(), "月": ec.getMonthHideGan(),
                     "日": ec.getDayHideGan(), "时": ec.getTimeHideGan()},
            "十神": {"年干": ec.getYearShiShenGan(), "月干": ec.getMonthShiShenGan(),
                     "时干": ec.getTimeShiShenGan(), "月支": ec.getMonthShiShenZhi(),
                     "日支": ec.getDayShiShenZhi(), "时支": ec.getTimeShiShenZhi()},
        }
    else:
        out["bazi_note"] = "缺出生时辰，未排时柱；喜用神须注明「未作精算」"
    return out


def _gan_ke(a, b):
    """天干五行相克，不论方向。"""
    wa, wb = WU_XING_GAN[a], WU_XING_GAN[b]
    return KE[wa] == wb or KE[wb] == wa


def relations(day, person):
    """日柱对某人年支、日柱的冲合刑害关系。合与破可并存，故并列返回。"""
    dz, pz = day["day_zhi"], person["year_zhi"]
    found = []
    if chong(dz) == pz:
        found.append("六冲")
    if dz == pz:
        found.append("日值本命")
    if SAN_XING.get(dz) == pz:
        found.append("自刑" if dz == pz else "三刑")
    if LIU_HAI.get(dz) == pz:
        found.append("六害")
    if XIANG_PO.get(dz) == pz:
        found.append("相破")
    if any(dz in ju and pz in ju and dz != pz for ju in SAN_HE_JU):
        found.append("三合")
    if LIU_HE[dz] == pz:
        found.append("六合")
    return {
        "name": person["name"],
        "role": person["role"],
        "zodiac": person["zodiac"],
        "relations": found or ["无"],
        "天克地冲": chong(day["day_zhi"]) == person["day_zhi"]
                    and _gan_ke(day["day_gan"], person["day_gan"]),
        "太岁": tai_sui(day, person),
    }


def tai_sui(day, person):
    """流年太岁：当年年支与本命年支相同为值太岁，相冲为冲太岁。"""
    year_zhi = day["ganzhi"]["year"][1]
    if year_zhi == person["year_zhi"]:
        return "值太岁"
    if chong(year_zhi) == person["year_zhi"]:
        return "冲太岁"
    return None


def hour_chart(day, avoid_zodiacs=(), daytime=None):
    """以日支起青龙、查时支定时辰黄道黑道，并标注冲破与贵人三合六合。

    黑道时不作一票否决，只记入 demerits：择时时优先取黄道，黄道尽被冲破时仍可降级取用。
    daytime 给定可用时支时，此外的时辰记为排除，避免选出夜间无法行事的钟点。
    """
    dz, dg = day["day_zhi"], day["day_gan"]
    # 冲某人生肖的是与其年支相冲的那个时支
    avoid = {chong(zhi_of_zodiac(z)): z for z in avoid_zodiacs if z in SHENG_XIAO}
    base = zi(QING_LONG_START[dz])
    out = []
    for i, hz in enumerate(ZHI):
        ts = TIAN_SHEN[(i - base) % 12]
        item = {"zhi": hz, "range": HOUR_RANGE[hz], "tianshen": ts,
                "tianshen_type": "黄道" if ts in HUANG_DAO else "黑道",
                "reasons": [], "demerits": [], "excluded": False, "exclude_reasons": []}
        if ts in HUANG_DAO:
            item["reasons"].append("%s黄道时" % ts)
        else:
            item["demerits"].append("%s黑道时" % ts)
        if hz in TIAN_YI[dg]:
            item["reasons"].append("日干%s之天乙贵人临时支%s" % (dg, hz))
        if any(hz in ju and dz in ju and hz != dz for ju in SAN_HE_JU):
            item["reasons"].append("时支%s与日支%s三合" % (hz, dz))
        if LIU_HE[dz] == hz:
            item["reasons"].append("时支%s与日支%s六合" % (hz, dz))
        if hz == chong(dz):
            item["excluded"] = True
            item["exclude_reasons"].append("时支冲日支%s，为日破时" % dz)
        if hz in avoid:
            item["excluded"] = True
            item["exclude_reasons"].append("时支%s冲主事人生肖%s" % (hz, avoid[hz]))
        if daytime is not None and hz not in daytime:
            item["excluded"] = True
            item["exclude_reasons"].append("%s时（%s）非白天可行事之时" % (hz, HOUR_RANGE[hz]))
        out.append(item)
    return out
