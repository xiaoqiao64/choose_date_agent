# -*- coding: utf-8 -*-
"""almanac.py 单元测试。

写法上刻意避免「把模块里的表再抄一遍来断言」这种同义反复。三类断言：

1. **口诀独立转写**——期望值直接照 program.md 参考表的口诀在本文件里重新写一遍，
   与被测模块的常量各自独立，抄错一处就会打架。
2. **不变式**——从命理定义本身推出的性质，如六冲互为对合、月破恒等于建星「破」、
   四离四绝每年各四日、黄道黑道各六神。这类断言不依赖任何具体数值。
3. **外部对照**——建星与黄道黑道拿 lunar-python 当独立参照物全量比对。

运行：.venv/bin/python -m unittest discover -s tests -v
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from lunar_python import Solar

import almanac as A

ALL_ZHI = "子丑寅卯辰巳午未申酉戌亥"
ALL_GAN = "甲乙丙丁戊己庚辛壬癸"


def day(day_gan="甲", day_zhi="子", year_gz="丙午"):
    """构造 relations / hour_chart 所需的最小日盘。"""
    return {"day_gan": day_gan, "day_zhi": day_zhi,
            "ganzhi": {"year": year_gz, "day": day_gan + day_zhi}}


def person(year_zhi="子", day_gz="甲子", name="某人", role="primary"):
    return {"name": name, "role": role, "year_zhi": year_zhi,
            "zodiac": A.zodiac_of(year_zhi),
            "day_gan": day_gz[0], "day_zhi": day_gz[1]}


class TestZhiHelpers(unittest.TestCase):
    """zi / chong / zodiac_of / zhi_of_zodiac"""

    def test_zi_是地支序号(self):
        self.assertEqual(A.zi("子"), 0)
        self.assertEqual(A.zi("卯"), 3)
        self.assertEqual(A.zi("亥"), 11)

    def test_chong_合口诀六对(self):
        # 参考表：子午、丑未、寅申、卯酉、辰戌、巳亥
        for a, b in [("子", "午"), ("丑", "未"), ("寅", "申"),
                     ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]:
            self.assertEqual(A.chong(a), b, "%s 应冲 %s" % (a, b))
            self.assertEqual(A.chong(b), a, "六冲须对称")

    def test_chong_是对合且无自冲(self):
        for z in ALL_ZHI:
            self.assertEqual(A.chong(A.chong(z)), z, "冲两次须回到自身")
            self.assertNotEqual(A.chong(z), z, "地支不自冲")

    def test_生肖与地支互转(self):
        self.assertEqual(A.zodiac_of("子"), "鼠")
        self.assertEqual(A.zodiac_of("寅"), "虎")
        self.assertEqual(A.zodiac_of("午"), "马")
        self.assertEqual(A.zhi_of_zodiac("兔"), "卯")
        for z in ALL_ZHI:
            self.assertEqual(A.zhi_of_zodiac(A.zodiac_of(z)), z)


class TestDateHelpers(unittest.TestCase):
    """parse_date / date_range"""

    def test_parse_date(self):
        self.assertEqual(A.parse_date("2026-11-14"), datetime.date(2026, 11, 14))
        self.assertEqual(A.parse_date("2026-01-01"), datetime.date(2026, 1, 1))

    def test_date_range_首尾均含(self):
        r = A.date_range("2026-11-01", "2026-11-03")
        self.assertEqual(r, [datetime.date(2026, 11, d) for d in (1, 2, 3)])

    def test_date_range_单日与空区间(self):
        self.assertEqual(len(A.date_range("2026-11-14", "2026-11-14")), 1)
        self.assertEqual(A.date_range("2026-11-14", "2026-11-13"), [])

    def test_date_range_跨年跨月(self):
        r = A.date_range("2026-12-30", "2027-01-02")
        self.assertEqual(len(r), 4)
        self.assertEqual(r[-1], datetime.date(2027, 1, 2))


class TestSiLiSiJue(unittest.TestCase):
    """_si_li_si_jue：四离＝二分二至前一日，四绝＝四立前一日"""

    def test_具体日期(self):
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 3, 19)), ("四离", "春分"))
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 12, 21)), ("四离", "冬至"))
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 2, 3)), ("四绝", "立春"))
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 11, 6)), ("四绝", "立冬"))

    def test_寻常日不命中(self):
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 11, 14)), (None, None))

    def test_交节当日本身不算(self):
        # 立冬当日是「四绝」的次日，不该再算四绝
        self.assertEqual(A._si_li_si_jue(datetime.date(2026, 11, 7)), (None, None))

    def test_每年各四日(self):
        for year in (2025, 2026, 2027):
            li = jue = 0
            d = datetime.date(year, 1, 1)
            while d <= datetime.date(year, 12, 31):
                kind, _ = A._si_li_si_jue(d)
                li += kind == "四离"
                jue += kind == "四绝"
                d += datetime.timedelta(days=1)
            self.assertEqual(li, 4, "%d 年四离应为 4 日" % year)
            self.assertEqual(jue, 4, "%d 年四绝应为 4 日" % year)


class TestMonthShenSha(unittest.TestCase):
    """_month_shen_sha：月家吉神凶煞。期望值照 program.md 参考表口诀独立转写。"""

    def ji(self, month_zhi, gan, zhi):
        return A._month_shen_sha(month_zhi, gan, zhi, gan + zhi)[0]

    def xiong(self, month_zhi, gan, zhi):
        return A._month_shen_sha(month_zhi, gan, zhi, gan + zhi)[1]

    def test_天赦_春戊寅夏甲午秋戊申冬甲子(self):
        for months, gz in [("寅卯辰", "戊寅"), ("巳午未", "甲午"),
                           ("申酉戌", "戊申"), ("亥子丑", "甲子")]:
            for mz in months:
                self.assertIn("天赦", self.ji(mz, gz[0], gz[1]),
                              "%s月 %s 应为天赦" % (mz, gz))

    def test_天赦_错季不算(self):
        # 甲子是冬月天赦，放在春月（寅）不该命中
        self.assertNotIn("天赦", self.ji("寅", "甲", "子"))

    def test_月德_寅午戌丙申子辰壬亥卯未甲巳酉丑庚(self):
        expect = {"寅": "丙", "午": "丙", "戌": "丙", "申": "壬", "子": "壬", "辰": "壬",
                  "亥": "甲", "卯": "甲", "未": "甲", "巳": "庚", "酉": "庚", "丑": "庚"}
        for mz, gan in expect.items():
            self.assertIn("月德", self.ji(mz, gan, "寅"), "%s月月德在%s" % (mz, gan))
            for other in ALL_GAN:
                if other != gan:
                    self.assertNotIn("月德", self.ji(mz, other, "寅"))

    def test_月德合_是月德之干合(self):
        # 甲己、乙庚、丙辛、丁壬、戊癸相合
        expect = {"寅": "辛", "午": "辛", "戌": "辛", "申": "丁", "子": "丁", "辰": "丁",
                  "亥": "己", "卯": "己", "未": "己", "巳": "乙", "酉": "乙", "丑": "乙"}
        for mz, gan in expect.items():
            self.assertIn("月德合", self.ji(mz, gan, "寅"), "%s月月德合在%s" % (mz, gan))

    def test_天德_四仲月临地支且无合(self):
        # 卯月天德在申日、午月在亥日、酉月在寅日、子月在巳日，皆为地支，无干可合
        for mz, zhi in [("卯", "申"), ("午", "亥"), ("酉", "寅"), ("子", "巳")]:
            got = self.ji(mz, "甲", zhi)
            self.assertIn("天德", got, "%s月天德应临%s日" % (mz, zhi))
        for mz in "子午卯酉":
            for gan in ALL_GAN:
                self.assertNotIn("天德合", self.ji(mz, gan, "寅"),
                                 "四仲月天德临支，不该有天德合")

    def test_天德_其余八月临天干且有合(self):
        expect = {"寅": "丁", "辰": "壬", "巳": "辛", "未": "甲",
                  "申": "癸", "戌": "丙", "亥": "乙", "丑": "庚"}
        for mz, gan in expect.items():
            self.assertIn("天德", self.ji(mz, gan, "寅"))
            self.assertIn("天德合", self.ji(mz, A.GAN_HE[gan], "寅"))

    def test_月破_日支冲月支(self):
        for mz in ALL_ZHI:
            self.assertIn("月破", self.xiong(mz, "甲", A.chong(mz)))
            self.assertNotIn("月破", self.xiong(mz, "甲", mz))

    def test_四废_春庚申辛酉夏壬子癸亥秋甲寅乙卯冬丙午丁巳(self):
        expect = {"寅卯辰": ["庚申", "辛酉"], "巳午未": ["壬子", "癸亥"],
                  "申酉戌": ["甲寅", "乙卯"], "亥子丑": ["丙午", "丁巳"]}
        for months, pairs in expect.items():
            for mz in months:
                for gz in pairs:
                    self.assertIn("四废", self.xiong(mz, gz[0], gz[1]),
                                  "%s月 %s 应为四废" % (mz, gz))

    def test_受死_正戌二辰三亥四巳五子六午七丑八未九寅十申冬卯腊酉(self):
        expect = dict(zip("寅卯辰巳午未申酉戌亥子丑", "戌辰亥巳子午丑未寅申卯酉"))
        for mz, zhi in expect.items():
            self.assertIn("受死", self.xiong(mz, "甲", zhi), "%s月受死在%s日" % (mz, zhi))
            for other in ALL_ZHI:
                if other != zhi:
                    self.assertNotIn("受死", self.xiong(mz, "甲", other))

    def test_复日_取月建本气之干(self):
        # 正甲、二乙、三戊、四丙、五丁、六己、七庚、八辛、九戊、十壬、冬癸、腊己
        expect = dict(zip("寅卯辰巳午未申酉戌亥子丑", "甲乙戊丙丁己庚辛戊壬癸己"))
        for mz, gan in expect.items():
            self.assertIn("复日", self.xiong(mz, gan, "寅"), "%s月复日在%s日" % (mz, gan))

    def test_重日_巳亥日不论月份(self):
        for mz in ALL_ZHI:
            self.assertIn("重日", self.xiong(mz, "甲", "巳"))
            self.assertIn("重日", self.xiong(mz, "甲", "亥"))
            self.assertNotIn("重日", self.xiong(mz, "甲", "子"))

    def test_三合六合_取日支与月支(self):
        # 寅午戌三合，寅亥六合
        self.assertIn("三合", self.ji("寅", "甲", "午"))
        self.assertIn("三合", self.ji("寅", "甲", "戌"))
        self.assertIn("六合", self.ji("寅", "甲", "亥"))
        self.assertNotIn("三合", self.ji("寅", "甲", "寅"), "同支不算三合")
        self.assertNotIn("三合", self.ji("寅", "甲", "子"))


class TestXingJiaStatus(unittest.TestCase):
    """xing_jia_status：正七迎鸡兔，二八虎与猴，三九蛇共猪，四十龙合狗，五十一牛羊，六十二鼠马"""

    DA_LI = {"鸡": (1, 7), "兔": (1, 7), "虎": (2, 8), "猴": (2, 8),
             "蛇": (3, 9), "猪": (3, 9), "龙": (4, 10), "狗": (4, 10),
             "牛": (5, 11), "羊": (5, 11), "鼠": (6, 12), "马": (6, 12)}

    def test_大利月对上口诀(self):
        for zodiac, months in self.DA_LI.items():
            for m in months:
                self.assertEqual(A.xing_jia_status(zodiac, m), "大利月",
                                 "属%s农历%d月应为大利月" % (zodiac, m))

    def test_自大利月起顺推六阶(self):
        # 属兔大利月为正月，则二月妨媒人、三月妨翁姑……六月妨女身
        expect = ["大利月", "妨媒人", "妨翁姑", "妨父母", "妨夫主", "妨女身"]
        for i, label in enumerate(expect):
            self.assertEqual(A.xing_jia_status("兔", 1 + i), label)

    def test_每属相十二月中恰两个大利月且相隔六月(self):
        for zodiac in self.DA_LI:
            hits = [m for m in range(1, 13) if A.xing_jia_status(zodiac, m) == "大利月"]
            self.assertEqual(len(hits), 2, "属%s应有两个大利月" % zodiac)
            self.assertEqual(hits[1] - hits[0], 6)

    def test_未知属相返回None(self):
        self.assertIsNone(A.xing_jia_status("麒麟", 1))


class TestGanKe(unittest.TestCase):
    """_gan_ke：天干五行相克，不论方向"""

    def test_相克成立且双向(self):
        for a, b in [("甲", "戊"), ("戊", "壬"), ("壬", "丙"), ("丙", "庚"), ("庚", "甲")]:
            self.assertTrue(A._gan_ke(a, b), "%s 与 %s 应相克" % (a, b))
            self.assertTrue(A._gan_ke(b, a), "相克不论方向")

    def test_同行与相生不算克(self):
        self.assertFalse(A._gan_ke("甲", "乙"), "同为木")
        self.assertFalse(A._gan_ke("甲", "丙"), "木生火，非克")
        self.assertFalse(A._gan_ke("壬", "甲"), "水生木，非克")


class TestRelations(unittest.TestCase):
    """relations：日柱对本命年支的冲合刑害"""

    def rel(self, day_zhi, year_zhi):
        return A.relations(day(day_zhi=day_zhi), person(year_zhi=year_zhi))["relations"]

    def test_各关系分别命中(self):
        self.assertEqual(self.rel("子", "午"), ["六冲"])
        self.assertEqual(self.rel("子", "未"), ["六害"])
        self.assertEqual(self.rel("子", "酉"), ["相破"])
        self.assertEqual(self.rel("子", "辰"), ["三合"])
        self.assertEqual(self.rel("子", "丑"), ["六合"])
        self.assertEqual(self.rel("子", "卯"), ["三刑"])
        self.assertEqual(self.rel("子", "寅"), ["无"])

    def test_日值本命与自刑并列(self):
        self.assertEqual(self.rel("辰", "辰"), ["日值本命", "自刑"])
        self.assertEqual(self.rel("子", "子"), ["日值本命"], "子非自刑之支")

    def test_刑害可并存(self):
        # 寅巳既是三刑又是六害
        self.assertEqual(self.rel("寅", "巳"), ["三刑", "六害"])

    def test_相破不得误判刑害对(self):
        # 曾用「相差三位」概括相破，会把子卯（刑）、寅巳（刑害）、申亥（害）误判为破
        for a, b in [("子", "卯"), ("寅", "巳"), ("申", "亥"), ("辰", "未"), ("午", "酉")]:
            self.assertNotIn("相破", self.rel(a, b), "%s%s 不是相破" % (a, b))
            self.assertNotIn("相破", self.rel(b, a))

    def test_相破六对且对称(self):
        for a, b in [("子", "酉"), ("卯", "午"), ("寅", "亥"),
                     ("巳", "申"), ("丑", "辰"), ("未", "戌")]:
            self.assertIn("相破", self.rel(a, b))
            self.assertIn("相破", self.rel(b, a))

    def test_天克地冲_须干克且支冲(self):
        # 甲子日 vs 庚午日柱：庚金克甲木，子午相冲
        r = A.relations(day("甲", "子"), person(year_zhi="寅", day_gz="庚午"))
        self.assertTrue(r["天克地冲"])

    def test_天克地冲_干不克则不成立(self):
        # 支虽冲，甲木生丙火非克
        r = A.relations(day("甲", "子"), person(year_zhi="寅", day_gz="丙午"))
        self.assertFalse(r["天克地冲"])

    def test_天克地冲_支不冲则不成立(self):
        r = A.relations(day("甲", "子"), person(year_zhi="寅", day_gz="庚申"))
        self.assertFalse(r["天克地冲"])

    def test_原样带出人员标识(self):
        r = A.relations(day(), person(name="新娘", role="primary", year_zhi="卯"))
        self.assertEqual((r["name"], r["role"], r["zodiac"]), ("新娘", "primary", "兔"))


class TestTaiSui(unittest.TestCase):
    """tai_sui：流年年支与本命年支相同为值太岁，相冲为冲太岁"""

    def test_值太岁(self):
        self.assertEqual(A.tai_sui(day(year_gz="丙午"), person(year_zhi="午")), "值太岁")

    def test_冲太岁(self):
        self.assertEqual(A.tai_sui(day(year_gz="丙午"), person(year_zhi="子")), "冲太岁")

    def test_无涉(self):
        self.assertIsNone(A.tai_sui(day(year_gz="丙午"), person(year_zhi="寅")))


class TestDayChart(unittest.TestCase):
    """day_chart：单日排盘"""

    def test_基准日排盘(self):
        c = A.day_chart(datetime.date(2026, 11, 14))
        self.assertEqual(c["solar"], "2026-11-14")
        self.assertEqual(c["weekday"], "周六")
        self.assertEqual(c["lunar"], "十月初六")
        self.assertEqual(c["ganzhi"], {"year": "丙午", "month": "己亥", "day": "壬辰"})
        self.assertEqual(c["jieqi_month"], {"month_zhi": "亥", "month_index": 10,
                                            "current_jie": "立冬", "season": "冬"})
        self.assertEqual(c["zhixing"], "执")
        self.assertEqual((c["tianshen"], c["tianshen_type"]), ("司命", "黄道"))
        self.assertEqual(c["chong"], {"zhi": "戌", "zodiac": "狗", "sha": "南"})

    def test_闰月不重复加闰字(self):
        c = A.day_chart(datetime.date(2028, 6, 23))
        self.assertTrue(c["leap_month"])
        self.assertEqual(c["lunar"], "闰五月初一")
        self.assertEqual(A.day_chart(datetime.date(2023, 3, 22))["lunar"], "闰二月初一")

    def test_当前节须与月建一致_含交节当日(self):
        # 2026-11-07 为立冬当日，月建已进亥，当前节必须同步报立冬
        c = A.day_chart(datetime.date(2026, 11, 7))
        self.assertEqual(c["jieqi_month"]["month_zhi"], "亥")
        self.assertEqual(c["jieqi_month"]["current_jie"], "立冬")
        c = A.day_chart(datetime.date(2026, 2, 4))
        self.assertEqual(c["jieqi_month"]["current_jie"], "立春")

    def test_交节当日建星重复一日(self):
        # 参考表：交节之日建星重复一日。立冬 2026-11-07，与前一日同值「开」
        self.assertEqual(A.day_chart(datetime.date(2026, 11, 6))["zhixing"], "开")
        self.assertEqual(A.day_chart(datetime.date(2026, 11, 7))["zhixing"], "开")

    def test_月建之日必为建星建(self):
        seen = set()
        for d in A.date_range("2026-01-01", "2026-12-31"):
            c = A.day_chart(d)
            if c["day_zhi"] == c["jieqi_month"]["month_zhi"]:
                self.assertEqual(c["zhixing"], "建")
                seen.add(c["jieqi_month"]["month_zhi"])
        self.assertEqual(len(seen), 12, "一年应覆盖十二个月建")

    def test_月破恒等于建星破(self):
        for d in A.date_range("2026-01-01", "2026-12-31"):
            c = A.day_chart(d)
            self.assertEqual("月破" in c["xiongsha"], c["zhixing"] == "破", c["solar"])

    def test_四离四绝写入凶煞并附节气(self):
        c = A.day_chart(datetime.date(2026, 11, 6))
        self.assertIn("四绝", c["xiongsha"])
        self.assertEqual(c["extra"]["四绝"], "立冬前一日")
        c = A.day_chart(datetime.date(2026, 3, 19))
        self.assertIn("四离", c["xiongsha"])
        self.assertEqual(c["extra"]["四离"], "春分前一日")

    def test_三娘煞按农历日(self):
        for d in A.date_range("2026-01-01", "2026-12-31"):
            c = A.day_chart(d)
            self.assertEqual(c["extra"]["三娘煞"],
                             c["lunar_day"] in (3, 7, 13, 18, 22, 27), c["solar"])

    def test_杨公忌按农历月日(self):
        # 正十三、二十一、三初九、四初七、五初五、六初三、七初一、七廿九、
        # 八廿七、九廿五、十廿三、冬廿一、腊十九
        expect = {1: {13}, 2: {11}, 3: {9}, 4: {7}, 5: {5}, 6: {3},
                  7: {1, 29}, 8: {27}, 9: {25}, 10: {23}, 11: {21}, 12: {19}}
        for d in A.date_range("2026-01-01", "2026-12-31"):
            c = A.day_chart(d)
            want = c["lunar_day"] in expect[c["lunar_month"]]
            self.assertEqual(c["extra"]["杨公忌"], want, c["solar"])

    def test_行嫁月仅在给定女方属相时出现(self):
        self.assertNotIn("行嫁月", A.day_chart(datetime.date(2026, 11, 14))["extra"])
        c = A.day_chart(datetime.date(2026, 11, 14), bride_zodiac="兔")
        self.assertEqual(c["extra"]["行嫁月"], A.xing_jia_status("兔", c["lunar_month"]))

    def test_自算神煞不与库返回值重复(self):
        # 月家天德与黄道十二神的天德（宝光）同名异物，前者本就该出现在吉神里，故排除在外
        leaked = A.LIB_TIAN_SHEN_NAMES - {"天德"}
        for d in A.date_range("2026-01-01", "2026-06-30"):
            c = A.day_chart(d)
            for names in (c["jishen"], c["xiongsha"]):
                self.assertEqual(len(names), len(set(names)), "%s 神煞重复" % c["solar"])
                self.assertFalse(set(names) & leaked,
                                 "%s 黄道黑道神名不应混入吉神凶煞" % c["solar"])
                self.assertNotIn("致死", names, "库中致死与受死定法不符，应已剔除")
                self.assertNotIn("无", names)

    def test_两个天德同名异物不致混淆(self):
        # 黄道十二神的天德一律写作「天德(宝光)」并只出现在 tianshen 字段；
        # 吉神里的「天德」是月家天德。2026-01-06 丑月庚辰日，月家天德在庚，而当日黄道神为白虎。
        c = A.day_chart(datetime.date(2026, 1, 6))
        self.assertIn("天德", c["jishen"], "丑月庚日应得月家天德")
        self.assertEqual(c["tianshen"], "白虎")
        self.assertNotIn("宝光", c["jishen"] + c["xiongsha"])
        self.assertTrue(all("天德(宝光)" != x for x in c["jishen"]))
        for d in A.date_range("2026-01-01", "2026-03-31"):
            day_ = A.day_chart(d)
            if day_["tianshen"] == "天德(宝光)":
                break
        else:
            self.fail("三个月内应出现天德(宝光)值日")
        self.assertEqual(day_["tianshen_type"], "黄道")

    def test_建星与天神以lunar_python为参照全量比对(self):
        d, last = datetime.date(2024, 1, 1), datetime.date(2027, 12, 31)
        n = 0
        while d <= last:
            lu = Solar.fromYmd(d.year, d.month, d.day).getLunar()
            c = A.day_chart(d)
            self.assertEqual(c["zhixing"], lu.getZhiXing(), "%s 建星不符" % d)
            self.assertEqual(c["tianshen"].replace("(宝光)", ""), lu.getDayTianShen(),
                             "%s 黄道黑道神不符" % d)
            self.assertEqual(c["tianshen_type"], lu.getDayTianShenType(), "%s 黄黑不符" % d)
            n += 1
            d += datetime.timedelta(days=1)
        self.assertGreater(n, 1400)


class TestPersonChart(unittest.TestCase):
    """person_chart：人员命盘"""

    def test_含时辰者排全四柱(self):
        p = A.person_chart({"name": "新娘", "role": "primary", "gender": "female",
                            "birth": "1999-07-08", "birth_time": "14:30"})
        self.assertEqual(p["year_ganzhi"], "己卯")
        self.assertEqual(p["zodiac"], "兔")
        self.assertEqual(p["day_ganzhi"], "辛酉")
        self.assertEqual(p["hour_ganzhi"], "乙未")
        self.assertTrue(p["has_hour"])
        self.assertEqual(p["bazi"]["四柱"], ["己卯", "辛未", "辛酉", "乙未"])
        self.assertEqual(p["bazi"]["日主"], "辛")
        self.assertNotIn("bazi_note", p)

    def test_缺时辰者不排时柱并留注记(self):
        p = A.person_chart({"name": "甲", "birth": "1970-05-02"})
        self.assertFalse(p["has_hour"])
        self.assertNotIn("bazi", p)
        self.assertIn("未作精算", p["bazi_note"])

    def test_角色与姓名有默认值(self):
        p = A.person_chart({"birth": "1970-05-02"})
        self.assertEqual(p["role"], "secondary")
        self.assertEqual(p["name"], "未具名")

    def test_年支取立春分界(self):
        # 2026 立春在 2 月 4 日，春节在 2 月 17 日；2 月 10 日两种分界不同
        p = A.person_chart({"birth": "2026-02-10"})
        self.assertEqual(p["zodiac"], "马", "冲克须按立春分界")
        self.assertIn("属蛇", p["zodiac_note"])

    def test_分界一致时不加注记(self):
        self.assertNotIn("zodiac_note", A.person_chart({"birth": "1999-07-08"}))

    def test_年支与生肖自洽(self):
        p = A.person_chart({"birth": "1987-07-05", "birth_time": "17:00"})
        self.assertEqual(p["year_zhi"], p["year_ganzhi"][1])
        self.assertEqual(p["zodiac"], A.zodiac_of(p["year_zhi"]))
        self.assertEqual(p["day_gan"] + p["day_zhi"], p["day_ganzhi"])


class TestHourChart(unittest.TestCase):
    """hour_chart：时辰盘"""

    def test_十二时辰齐备且钟点正确(self):
        hours = A.hour_chart(day())
        self.assertEqual([h["zhi"] for h in hours], list(ALL_ZHI))
        self.assertEqual(hours[A.zi("子")]["range"], "23:00-01:00")
        self.assertEqual(hours[A.zi("辰")]["range"], "07:00-09:00")
        self.assertEqual(hours[A.zi("酉")]["range"], "17:00-19:00")

    def test_以日支起青龙(self):
        # 口诀同黄道十二神，改以日支起算：日支子者自申时起青龙
        hours = {h["zhi"]: h["tianshen"] for h in A.hour_chart(day(day_zhi="子"))}
        self.assertEqual(hours["申"], "青龙")
        self.assertEqual(hours["酉"], "明堂")
        self.assertEqual(hours["子"], "金匮")
        hours = {h["zhi"]: h["tianshen"] for h in A.hour_chart(day(day_zhi="巳"))}
        self.assertEqual(hours["午"], "青龙", "巳亥午中寻")

    def test_黄道黑道各六神(self):
        for dz in ALL_ZHI:
            hours = A.hour_chart(day(day_zhi=dz))
            huang = [h for h in hours if h["tianshen_type"] == "黄道"]
            self.assertEqual(len(huang), 6, "%s日黄道时应六个" % dz)
            self.assertEqual(len(hours) - len(huang), 6)

    def test_日破时被排除(self):
        for dz in ALL_ZHI:
            hours = {h["zhi"]: h for h in A.hour_chart(day(day_zhi=dz))}
            broken = hours[A.chong(dz)]
            self.assertTrue(broken["excluded"])
            self.assertTrue(any("日破时" in r for r in broken["exclude_reasons"]))

    def test_冲主事人生肖者被排除_排的是相冲之时支(self):
        # 避鼠，应排除午时（午冲子），而非子时本身
        hours = {h["zhi"]: h for h in A.hour_chart(day(day_zhi="辰"), avoid_zodiacs=["鼠"])}
        self.assertTrue(hours["午"]["excluded"])
        self.assertTrue(any("冲主事人生肖鼠" in r for r in hours["午"]["exclude_reasons"]))
        self.assertFalse(hours["子"]["excluded"], "子时本身不该被排除")

    def test_无效生肖被忽略(self):
        hours = A.hour_chart(day(day_zhi="辰"), avoid_zodiacs=["麒麟"])
        extra = [h for h in hours if h["excluded"] and h["zhi"] != A.chong("辰")]
        self.assertEqual(extra, [])

    def test_白天窗口排除夜间时辰(self):
        daytime = ["卯", "辰", "巳", "午", "未", "申", "酉"]
        hours = {h["zhi"]: h for h in A.hour_chart(day(day_zhi="辰"), daytime=daytime)}
        for z in "戌亥子丑寅":
            self.assertTrue(hours[z]["excluded"], "%s时应排除" % z)
            self.assertTrue(any("非白天" in r for r in hours[z]["exclude_reasons"]))
        for z in daytime:
            if z != A.chong("辰"):
                self.assertFalse(hours[z]["excluded"], "%s时不该排除" % z)

    def test_不给白天窗口则不按昼夜排除(self):
        hours = A.hour_chart(day(day_zhi="辰"))
        for h in hours:
            self.assertFalse(any("非白天" in r for r in h["exclude_reasons"]))

    def test_天乙贵人临时支(self):
        # 甲戊庚牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎
        expect = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
                  "丙": "亥酉", "丁": "亥酉", "壬": "卯巳", "癸": "卯巳", "辛": "午寅"}
        for gan, zhis in expect.items():
            hours = {h["zhi"]: h for h in A.hour_chart(day(day_gan=gan, day_zhi="辰"))}
            for z in ALL_ZHI:
                has = any("天乙贵人" in r for r in hours[z]["reasons"])
                self.assertEqual(has, z in zhis, "日干%s 时支%s 贵人判定有误" % (gan, z))

    def test_三合六合记入取用依据(self):
        hours = {h["zhi"]: h for h in A.hour_chart(day(day_zhi="辰"))}
        self.assertTrue(any("三合" in r for r in hours["申"]["reasons"]), "申子辰三合")
        self.assertTrue(any("三合" in r for r in hours["子"]["reasons"]))
        self.assertTrue(any("六合" in r for r in hours["酉"]["reasons"]), "辰酉六合")
        self.assertFalse(any("三合" in r for r in hours["辰"]["reasons"]), "同支不算三合")

    def test_黑道时只记减分不一票否决(self):
        hours = [h for h in A.hour_chart(day(day_zhi="辰"))
                 if h["tianshen_type"] == "黑道" and h["zhi"] != A.chong("辰")]
        self.assertTrue(hours)
        for h in hours:
            self.assertFalse(h["excluded"], "黑道时不该被排除，只记 demerits")
            self.assertTrue(any("黑道时" in d for d in h["demerits"]))


class TestConstantTables(unittest.TestCase):
    """常量表自洽性：这些表是玄学定法的载体，漏项或不对称会静默算错"""

    def test_十二项表均覆盖全部地支(self):
        for name in ("QING_LONG_START", "SEASON", "LIU_HE", "LIU_HAI", "XIANG_PO",
                     "SAN_XING", "TIAN_DE", "YUE_DE", "SHOU_SI", "HONG_SHA",
                     "CHONG_SANG", "HOUR_RANGE", "JIE_OF_MONTH"):
            self.assertEqual(set(getattr(A, name)), set(ALL_ZHI), "%s 未覆盖十二地支" % name)

    def test_合害破表对称(self):
        for name in ("LIU_HE", "LIU_HAI", "XIANG_PO", "GAN_HE"):
            table = getattr(A, name)
            for a, b in table.items():
                self.assertEqual(table[b], a, "%s 中 %s-%s 不对称" % (name, a, b))

    def test_六合六害的序数性质(self):
        for a, b in A.LIU_HE.items():
            self.assertIn(A.zi(a) + A.zi(b), (1, 13), "六合两支序数和为 1 或 13")
        for a, b in A.LIU_HAI.items():
            self.assertEqual((A.zi(a) + A.zi(b)) % 12, 7, "六害两支序数和模十二为 7")

    def test_干合为五对(self):
        self.assertEqual(len(A.GAN_HE), 10)
        self.assertEqual(set(A.GAN_HE), set(ALL_GAN))
        for a, b in [("甲", "己"), ("乙", "庚"), ("丙", "辛"), ("丁", "壬"), ("戊", "癸")]:
            self.assertEqual(A.GAN_HE[a], b)

    def test_三合四局互不重叠且共十二支(self):
        self.assertEqual(len(A.SAN_HE_JU), 4)
        merged = set()
        for ju in A.SAN_HE_JU:
            self.assertEqual(len(ju), 3)
            self.assertFalse(merged & ju, "三合局之间不应重叠")
            merged |= ju
        self.assertEqual(merged, set(ALL_ZHI))

    def test_建星与天神各十二且黄黑对半(self):
        self.assertEqual(len(A.ZHI_XING), 12)
        self.assertEqual(len(set(A.ZHI_XING)), 12)
        self.assertEqual(len(A.TIAN_SHEN), 12)
        self.assertEqual(len(set(A.TIAN_SHEN)), 12)
        self.assertEqual(len(A.HUANG_DAO), 6)
        self.assertTrue(A.HUANG_DAO <= set(A.TIAN_SHEN))

    def test_天乙贵人覆盖十干且各两支(self):
        self.assertEqual(set(A.TIAN_YI), set(ALL_GAN))
        for gan, zhis in A.TIAN_YI.items():
            self.assertEqual(len(zhis), 2)
            self.assertTrue(set(zhis) <= set(ALL_ZHI))

    def test_行嫁月十二属相且六阶(self):
        self.assertEqual(set(A.XING_JIA_DA_LI), set(A.SHENG_XIAO))
        self.assertEqual(len(A.XING_JIA_LABEL), 6)
        self.assertEqual(A.XING_JIA_LABEL[0], "大利月")

    def test_节气月表与月建顺序一致(self):
        self.assertEqual(A.JIE_OF_MONTH["寅"], "立春")
        self.assertEqual(A.JIE_OF_MONTH["亥"], "立冬")
        self.assertEqual(A.MONTH_ZHI[0], "寅", "正月建寅")
        self.assertEqual(len(A.MONTH_ZHI), 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
