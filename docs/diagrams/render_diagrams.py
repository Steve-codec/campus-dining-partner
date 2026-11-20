"""Generate the course DFD and Chen ER figures as SVG and high-resolution PNG."""

import argparse
import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MODEL = json.loads((ROOT / "model.json").read_text(encoding="utf-8"))
ENTITIES = {item["id"]: item for item in MODEL["entities"]}
RELATIONSHIPS = {item["id"]: item for item in MODEL["relationships"]}
INK = "#202020"
SCALE = 2
FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"


class Figure:
    def __init__(self, name, width, height, title, subtitle):
        self.name, self.width, self.height = name, width, height
        self.svg = [
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f"<title>{html.escape(title)}</title>",
            '<rect width="100%" height="100%" fill="white"/>',
        ]
        self.image = Image.new("RGB", (width * SCALE, height * SCALE), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = {}
        self.text(width / 2, 42, title, 32)
        self.text(width / 2, 86, subtitle, 20)

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = ImageFont.truetype(FONT_PATH, round(size * SCALE))
        return self.fonts[size]

    def line(self, points, arrow=False, width=2):
        value = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(
            f'<polyline points="{value}" fill="none" stroke="{INK}" '
            f'stroke-width="{width}" stroke-linejoin="round"/>'
        )
        self.draw.line(
            [(round(x * SCALE), round(y * SCALE)) for x, y in points],
            fill=INK, width=round(width * SCALE),
        )
        if arrow:
            (x0, y0), (x1, y1) = points[-2:]
            angle = math.atan2(y1 - y0, x1 - x0)
            wings = [
                (x1, y1),
                (x1 - 13 * math.cos(angle - 0.42), y1 - 13 * math.sin(angle - 0.42)),
                (x1 - 13 * math.cos(angle + 0.42), y1 - 13 * math.sin(angle + 0.42)),
            ]
            self.polygon(wings, INK)

    def polygon(self, points, fill="white"):
        value = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(
            f'<polygon points="{value}" fill="{fill}" stroke="{INK}" stroke-width="2"/>'
        )
        self.draw.polygon(
            [(round(x * SCALE), round(y * SCALE)) for x, y in points],
            fill=fill, outline=INK, width=2 * SCALE,
        )

    def rect(self, cx, cy, width, height):
        x, y = cx - width / 2, cy - height / 2
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'fill="white" stroke="{INK}" stroke-width="2"/>'
        )
        self.draw.rectangle(
            [round(x * SCALE), round(y * SCALE),
             round((x + width) * SCALE), round((y + height) * SCALE)],
            fill="white", outline=INK, width=2 * SCALE,
        )

    def ellipse(self, cx, cy, width, height):
        self.svg.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{width / 2}" ry="{height / 2}" '
            f'fill="white" stroke="{INK}" stroke-width="2"/>'
        )
        self.draw.ellipse(
            [round((cx - width / 2) * SCALE), round((cy - height / 2) * SCALE),
             round((cx + width / 2) * SCALE), round((cy + height / 2) * SCALE)],
            fill="white", outline=INK, width=2 * SCALE,
        )

    def text(self, x, y, value, size=24, underline=False, background=False):
        lines = str(value).split("\n")
        for index, value_line in enumerate(lines):
            cy = y + (index - (len(lines) - 1) / 2) * size * 1.4
            font = self.font(size)
            text_width = self.draw.textlength(value_line, font=font) / SCALE
            if background:
                bx, by = x - text_width / 2 - 5, cy - size * 0.67
                self.svg.append(
                    f'<rect x="{bx}" y="{by}" width="{text_width + 10}" '
                    f'height="{size * 1.34}" fill="white"/>'
                )
                self.draw.rectangle(
                    [round(bx * SCALE), round(by * SCALE),
                     round((bx + text_width + 10) * SCALE),
                     round((by + size * 1.34) * SCALE)], fill="white",
                )
            self.svg.append(
                f'<text x="{x}" y="{cy}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="{size}" fill="{INK}" '
                'font-family="Heiti SC, PingFang SC, Noto Sans CJK SC, sans-serif">'
                f"{html.escape(value_line)}</text>"
            )
            self.draw.text(
                (round(x * SCALE), round(cy * SCALE)),
                value_line, font=font, fill=INK, anchor="mm",
            )
            if underline:
                self.line([(x - text_width / 2, cy + size * 0.65),
                           (x + text_width / 2, cy + size * 0.65)], width=1.4)

    def entity(self, entity_id, x, y, width=220, height=76):
        self.rect(x, y, width, height)
        self.text(x, y, ENTITIES[entity_id]["name"], 29)

    def relationship(self, relationship_id, x, y, width=160, height=92):
        self.polygon([(x - width / 2, y), (x, y - height / 2),
                      (x + width / 2, y), (x, y + height / 2)])
        self.text(x, y, RELATIONSHIPS[relationship_id]["name"], 26)

    def attribute(self, name, x, y, key=False, width=None):
        width = width or max(160, len(name) * 24 + 34)
        self.ellipse(x, y, width, 64)
        self.text(x, y, name, 23, underline=key)

    def card(self, x, y, value):
        self.text(x, y, value, 24, background=True)

    def actor(self, x, y, label, width=185, height=76):
        self.rect(x, y, width, height)
        self.text(x, y, label, 23)

    def process(self, x, y, label, width=208, height=112):
        self.ellipse(x, y, width, height)
        self.text(x, y, label, 23)

    def store(self, x, y, label, width=250, height=76):
        left, right = x - width / 2, x + width / 2
        top, bottom = y - height / 2, y + height / 2
        self.line([(right, top), (left, top), (left, bottom), (right, bottom)])
        self.line([(left + 13, top), (left + 13, bottom)])
        self.text(x + 5, y, label, 23)

    def save(self):
        self.svg.append("</svg>")
        (ROOT / f"{self.name}.svg").write_text("\n".join(self.svg), encoding="utf-8")
        self.image.save(ROOT / f"{self.name}.png", dpi=(240, 240))
        print(f"{self.name}: SVG + PNG ({self.width * SCALE} x {self.height * SCALE})")


ER_LEGEND = "矩形为实体，菱形为联系，椭圆为属性；下划线为实体标识，数字表示最大基数"


def er_global():
    f = Figure("er-00-global", 2200, 1450, "全局基本 E-R 图", "")
    # Draw all links before shapes.
    for points in [
        [(440, 650), (910, 540)], [(1070, 540), (1520, 650)],
        [(440, 680), (910, 680)], [(1070, 680), (1520, 680)],
        [(440, 710), (910, 820)], [(1070, 820), (1520, 710)],
        [(330, 642), (330, 246)], [(410, 200), (880, 200)],
        [(1100, 200), (1200, 200)], [(1360, 200), (1520, 200)],
        [(990, 238), (990, 410), (1550, 410)], [(1630, 456), (1630, 642)],
        [(330, 718), (330, 1150), (540, 1150)], [(700, 1150), (880, 1150)],
        [(1630, 718), (1630, 1104)], [(1550, 1150), (1100, 1150)],
        [(220, 680), (185, 680)], [(270, 718), (180, 868)],
        [(1630, 162), (1630, 132)], [(1740, 200), (1820, 200)],
        [(930, 162), (800, 132)], [(1050, 162), (1200, 132)],
        [(1740, 665), (1850, 610)], [(1740, 690), (1850, 750)],
        [(1680, 718), (1900, 870)],
        [(950, 1188), (850, 1288)], [(1030, 1188), (1150, 1288)],
    ]:
        f.line(points)
    for entity_id, x, y in [
        ("user", 330, 680), ("event", 1630, 680),
        ("stall", 990, 200), ("canteen", 1630, 200), ("tag", 990, 1150),
    ]:
        f.entity(entity_id, x, y)
    for relation_id, x, y in [
        ("hosts", 990, 540), ("registers", 990, 680), ("reviews", 990, 820),
        ("favorites", 330, 200), ("contains", 1280, 200), ("venue", 1630, 410),
        ("prefers", 620, 1150), ("labels", 1630, 1150),
    ]:
        f.relationship(relation_id, x, y)
    for x, y, value in [
        (565, 597, "1"), (1405, 597, "N"), (565, 656, "M"), (1405, 656, "N"),
        (565, 765, "M"), (1405, 765, "N"), (305, 450, "M"), (680, 176, "N"),
        (1450, 176, "1"), (1155, 176, "N"), (1250, 387, "1"), (1657, 545, "N"),
        (305, 955, "M"), (790, 1125, "N"), (1657, 955, "M"), (1300, 1125, "N"),
    ]:
        f.card(x, y, value)
    for name, x, y, key in [
        ("用户编号", 105, 680, True), ("偏好时段", 180, 900, False),
        ("食堂编号", 1630, 100, True), ("食堂名称", 1900, 200, False),
        ("档口编号", 780, 100, True), ("档口名称", 1210, 100, False),
        ("饭局编号", 1930, 610, True), ("标题", 1930, 750, False),
        ("计划就餐时间", 1930, 900, False), ("标签编号", 850, 1320, True),
        ("标签名称", 1150, 1320, False),
    ]:
        f.attribute(name, x, y, key)
    f.text(1100, 1402, ER_LEGEND, 22)
    f.save()


def er_user_preferences():
    f = Figure("er-01-user-preferences", 1600, 820, "局部 E-R 图 用户与口味偏好", ER_LEGEND)
    for points in [
        [(510, 380), (720, 380)], [(880, 380), (1090, 380)],
        [(340, 342), (210, 210)], [(400, 342), (400, 190)],
        [(460, 342), (600, 210)], [(340, 418), (210, 588)],
        [(400, 418), (400, 648)], [(460, 418), (600, 588)],
        [(1140, 342), (1060, 210)], [(1260, 342), (1360, 210)],
    ]:
        f.line(points)
    f.entity("user", 400, 380)
    f.entity("tag", 1200, 380)
    f.relationship("prefers", 800, 380)
    f.card(600, 353, "M")
    f.card(1000, 353, "N")
    positions = [(200, 180), (400, 158), (600, 180), (200, 620), (400, 680), (600, 620)]
    for attr, (x, y) in zip(ENTITIES["user"]["attributes"], positions):
        f.attribute(attr["name"], x, y, attr.get("key", False))
    f.attribute("标签编号", 1050, 180, True)
    f.attribute("标签名称", 1370, 180)
    f.text(800, 775, "偏好时段为用户的单值属性；口味偏好多选，通过偏好联系表达", 23)
    f.save()


def er_venue():
    f = Figure("er-02-canteen-stall-meal", 1600, 1380, "局部 E-R 图 食堂 档口与饭局", ER_LEGEND)
    for points in [
        [(410, 270), (650, 270)], [(810, 270), (1010, 270)],
        [(1120, 308), (1120, 504)], [(1120, 596), (1120, 792)],
        [(300, 232), (300, 182)], [(300, 308), (300, 388)],
        [(1060, 232), (970, 182)], [(1180, 232), (1360, 182)],
        [(1010, 810), (780, 680)], [(1010, 830), (670, 830)],
        [(1010, 850), (730, 998)], [(1120, 868), (1120, 1118)],
        [(1230, 810), (1410, 680)], [(1230, 830), (1410, 898)],
        [(1230, 850), (1410, 1118)],
    ]:
        f.line(points)
    f.entity("canteen", 300, 270)
    f.entity("stall", 1120, 270)
    f.entity("event", 1120, 830)
    f.relationship("contains", 730, 270)
    f.relationship("venue", 1120, 550)
    f.card(520, 242, "1")
    f.card(915, 242, "N")
    f.card(1150, 410, "1")
    f.card(1150, 700, "N")
    for name, x, y, key in [
        ("食堂编号", 300, 150, True), ("食堂名称", 300, 420, False),
        ("档口编号", 950, 150, True), ("档口名称", 1390, 150, False),
        ("饭局编号", 760, 650, True), ("标题", 590, 830, False),
        ("计划就餐时间", 700, 1030, False), ("人数上限", 1120, 1150, False),
        ("说明", 1410, 650, False), ("取消时间", 1410, 930, False),
        ("创建时间", 1410, 1150, False),
    ]:
        f.attribute(name, x, y, key)
    f.text(800, 1285, "每场饭局只选择一个档口；所属食堂由档口确定，不在饭局中重复保存", 23)
    f.text(800, 1328, "取消时间为空表示未取消；当前饭局状态由取消时间和计划就餐时间计算", 23)
    f.save()


def er_registrations():
    f = Figure("er-03-host-and-registration", 1600, 880, "局部 E-R 图 发起与报名", ER_LEGEND)
    for points in [
        [(410, 390), (720, 230)], [(880, 230), (1190, 390)],
        [(410, 420), (720, 420)], [(880, 420), (1190, 420)],
        [(240, 382), (140, 252)], [(1360, 382), (1460, 252)],
        [(760, 443), (520, 638)], [(800, 466), (800, 708)],
        [(840, 443), (1080, 638)],
    ]:
        f.line(points)
    f.entity("user", 300, 420)
    f.entity("event", 1300, 420)
    f.relationship("hosts", 800, 230)
    f.relationship("registers", 800, 420)
    for x, y, value in [(540, 302, "1"), (1060, 302, "N"),
                         (560, 392, "M"), (1040, 392, "N")]:
        f.card(x, y, value)
    for name, x, y, key in [
        ("用户编号", 130, 220, True), ("饭局编号", 1470, 220, True),
        ("报名状态", 500, 670, False), ("最近报名时间", 800, 740, False),
        ("最近退出时间", 1100, 670, False),
    ]:
        f.attribute(name, x, y, key)
    f.text(800, 825, "发起饭局同时创建发起人报名记录；每个用户与每场饭局只保留一条报名记录", 22)
    f.save()


def er_favorites():
    f = Figure("er-04-stall-favorites", 1600, 700, "局部 E-R 图 档口收藏", ER_LEGEND)
    for points in [
        [(410, 320), (720, 320)], [(880, 320), (1190, 320)],
        [(240, 282), (160, 192)], [(1360, 282), (1440, 192)],
        [(800, 366), (800, 488)],
    ]:
        f.line(points)
    f.entity("user", 300, 320)
    f.entity("stall", 1300, 320)
    f.relationship("favorites", 800, 320)
    f.card(560, 292, "M")
    f.card(1040, 292, "N")
    f.attribute("用户编号", 150, 160, True)
    f.attribute("档口编号", 1450, 160, True)
    f.attribute("收藏时间", 800, 520)
    f.text(800, 645, "同一用户与同一档口只有一条收藏关联；取消收藏删除该关联", 23)
    f.save()


def er_tags_reviews():
    f = Figure("er-05-meal-tags-and-review", 1650, 1080, "局部 E-R 图 饭局标签与评价", ER_LEGEND)
    for points in [
        [(410, 270), (720, 270)], [(880, 270), (1190, 420)],
        [(410, 690), (720, 690)], [(880, 690), (1190, 470)],
        [(240, 232), (140, 182)], [(360, 232), (460, 182)],
        [(190, 690), (170, 690)], [(1410, 440), (1450, 440)],
        [(760, 713), (530, 888)], [(800, 736), (800, 958)],
        [(840, 713), (1070, 888)],
    ]:
        f.line(points)
    f.entity("tag", 300, 270)
    f.entity("user", 300, 690)
    f.entity("event", 1300, 440)
    f.relationship("labels", 800, 270)
    f.relationship("reviews", 800, 690)
    for x, y, value in [(560, 242, "N"), (1050, 323, "M"),
                         (560, 662, "M"), (1070, 525, "N")]:
        f.card(x, y, value)
    for name, x, y, key in [
        ("标签编号", 130, 150, True), ("标签名称", 470, 150, False),
        ("用户编号", 90, 690, True), ("饭局编号", 1530, 440, True),
        ("评分", 510, 920, False), ("评价内容", 800, 990, False),
        ("评价时间", 1090, 920, False),
    ]:
        f.attribute(name, x, y, key)
    f.text(825, 1035, "评价必须对应报名记录；每位用户对每场饭局只能评价一次", 22)
    f.save()


def dfd_context():
    f = Figure("dfd-00-context", 1600, 700, "系统上下文数据流图",
               "E1 为学生；E2 为通过初始化脚本提供基础资料的小组维护者")
    for points in [
        [(310, 320), (666, 320)], [(666, 420), (310, 420)],
        [(1290, 320), (934, 320)], [(934, 420), (1290, 420)],
    ]:
        f.line(points, arrow=True)
    f.actor(200, 370, "E1\n学生", 220, 150)
    f.process(800, 370, "P0\n校园饭搭子系统", 310, 200)
    f.actor(1400, 370, "E2\n基础资料维护者", 220, 150)
    f.text(480, 215, "F01/F03/F05\nF07/F09/F11\n业务请求", 22)
    f.text(480, 520, "F02/F04/F06\nF08/F10/F12\n业务结果", 22)
    f.text(1120, 255, "F13 基础资料", 22)
    f.text(1120, 495, "F14 导入结果", 22)
    f.text(800, 640, "请求与结果的完整组成见数据字典；上下文图不展开内部数据存储", 22)
    f.save()


def dfd_system():
    f = Figure("dfd-01-system", 1640, 1950, "系统第一层数据流图",
               "E1 与 D0 重复绘制以减少交叉线；D0 汇总 D1 至 D10，不新增数据表")
    for index, p in enumerate(MODEL["processes"]):
        y = 245 + index * 250
        f.line([(245, y - 22), (642, y - 22)], arrow=True)
        f.line([(648, y + 30), (245, y + 30)], arrow=True)
        if p["reads"]:
            f.line([(1270, y - 22), (838, y - 22)], arrow=True)
        if p["writes"]:
            f.line([(832, y + 30), (1270, y + 30)], arrow=True)
        f.actor(150, y, "E2\n资料维护者" if p["id"] == "P7" else "E1\n学生", 190, 100)
        f.process(740, y, f'{p["id"]}\n{p["name"]}', 210, 125)
        f.store(1425, y, "D0\n业务数据库", 310, 100)
        f.text(435, y - 60, p["input"], 20)
        f.text(435, y + 72, p["output"], 20)
        if p["reads"]:
            ids = p["reads"]
            lines = ["读 " + "/".join(ids[:5])]
            if len(ids) > 5:
                lines.append("/".join(ids[5:]))
            f.text(1060, y - 78, "\n".join(lines), 20)
        if p["writes"]:
            f.text(1060, y + 72, "写 " + "/".join(p["writes"]), 20)
    f.text(820, 1880, "圆形为处理，矩形为外部实体，开口双线框为数据存储，箭头表示数据流向", 22)
    f.save()


def dfd_registration():
    f = Figure("dfd-02-registration", 1680, 1180, "报名与退出第二层数据流图",
               "P3 分解为 P3.1 和 P3.2；F05 与 F06 分别按报名、退出拆分")
    for row, y in enumerate([340, 850]):
        f.line([(260, y - 24), (608, y - 24)], arrow=True)
        f.line([(612, y + 30), (260, y + 30)], arrow=True)
        f.line([(1220, y - 115), (1090, y - 115), (809, y - 28)], arrow=True)
        f.line([(1220, y + 105), (1110, y + 105), (817, y + 15)], arrow=True)
        f.line([(774, y + 53), (1020, y + 195), (1370, y + 195),
                (1370, y + 143)], arrow=True)
        f.actor(160, y, "E1\n学生", 200, 110)
        f.process(710, y, "P3.1\n报名" if row == 0 else "P3.2\n退出", 220, 130)
        f.store(1370, y - 115, "D4 饭局", 300, 76)
        f.store(1370, y + 105, "D5 报名记录", 300, 76)
        f.text(430, y - 62, "F05.1 报名请求" if row == 0 else "F05.2 退出请求", 21)
        f.text(430, y + 72, "F06.1 报名结果" if row == 0 else "F06.2 退出结果", 21)
        f.text(1050, y - 163,
               "就餐时间、取消时间、人数上限" if row == 0 else "发起人、就餐时间、取消时间", 20)
        f.text(1040, y + 40,
               "本人报名记录、当前报名人数" if row == 0 else "本人报名记录", 20,
               background=True)
        f.text(1110, y + 232,
               "报名状态、最近报名时间" if row == 0 else "退出状态、最近退出时间", 21)
    f.text(840, 1130, "首次报名插入记录，再次报名复用记录；发起人自动报名由 P2 处理", 22)
    f.save()


def main():
    global FONT_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default=FONT_PATH, help="Chinese TrueType/OpenType font path")
    args = parser.parse_args()
    FONT_PATH = args.font
    for render in [
        dfd_context, dfd_system, dfd_registration,
        er_global, er_user_preferences, er_venue, er_registrations,
        er_favorites, er_tags_reviews,
    ]:
        render()


if __name__ == "__main__":
    main()
