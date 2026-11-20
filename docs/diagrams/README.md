# 数据库设计图文件说明

本目录保存 step3 的三张数据流图和 step4 的六张 E-R 图。PNG 用于查看和插入课程报告，SVG 为可编辑矢量图源。

## 图文件

| 内容 | 图片 | 矢量图源 |
| --- | --- | --- |
| 系统上下文数据流图 | [PNG](./dfd-00-context.png) | [SVG](./dfd-00-context.svg) |
| 系统第一层数据流图 | [PNG](./dfd-01-system.png) | [SVG](./dfd-01-system.svg) |
| 报名与退出第二层数据流图 | [PNG](./dfd-02-registration.png) | [SVG](./dfd-02-registration.svg) |
| 全局基本 E-R 图 | [PNG](./er-00-global.png) | [SVG](./er-00-global.svg) |
| 用户与口味偏好局部 E-R 图 | [PNG](./er-01-user-preferences.png) | [SVG](./er-01-user-preferences.svg) |
| 食堂档口与饭局局部 E-R 图 | [PNG](./er-02-canteen-stall-meal.png) | [SVG](./er-02-canteen-stall-meal.svg) |
| 发起与报名局部 E-R 图 | [PNG](./er-03-host-and-registration.png) | [SVG](./er-03-host-and-registration.svg) |
| 档口收藏局部 E-R 图 | [PNG](./er-04-stall-favorites.png) | [SVG](./er-04-stall-favorites.svg) |
| 饭局标签与评价局部 E-R 图 | [PNG](./er-05-meal-tags-and-review.png) | [SVG](./er-05-meal-tags-and-review.svg) |

## 图例与模型

- E-R 图使用矩形实体、菱形联系和椭圆属性，下划线表示实体标识，连线上的数字表示最大基数。完整参与范围和关系模式见[数据库设计](../数据库设计.md)第 13 至 15 节。
- 数据流图使用外部实体、处理、数据存储和有向数据流。E1 为学生，E2 为基础资料维护者；D0 为 D1 至 D10 的逻辑汇总，重复框代表同一个实体或存储。
- [model.json](./model.json) 记录五个实体、八个联系、十个关系及七个处理的模型。
- [render_diagrams.py](./render_diagrams.py) 保存图形布局，并输出 SVG 和 PNG。修改模型或布局后执行脚本更新图片。

## 重新生成

在仓库根目录执行：

```bash
python3 docs/diagrams/render_diagrams.py
```

脚本使用 Pillow。默认读取 macOS 的 `/System/Library/Fonts/STHeiti Light.ttc`；使用其他中文字体时，通过 `--font` 传入字体文件路径：

```bash
python3 docs/diagrams/render_diagrams.py --font /path/to/chinese-font.ttf
```

PNG 以两倍绘图尺寸输出，并写入 240 DPI 信息。脚本直接覆盖同名的九组图文件。
