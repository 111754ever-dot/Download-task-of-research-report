# -*- coding: utf-8 -*-
"""
去重清理:删除下载文件夹里 Windows 自动生成的重复文件
(形如 '20260723-华创证券-xxx (1).pdf'、'xxx (2).pdf')。
每组同名文件只保留一份。用法:python dedup_files.py
"""
import os
import re
import config

folder = config.OUT_DIR
if not os.path.isdir(folder):
    raise SystemExit(f"找不到文件夹:{folder}")

# 匹配结尾的 " (数字)",例如 "名字 (1).pdf"
pat = re.compile(r"^(.*) \((\d+)\)(\.[^.]+)$")

files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

groups = {}
for f in files:
    m = pat.match(f)
    key = (m.group(1) + m.group(3)) if m else f    # 去掉 " (N)" 后的原名
    groups.setdefault(key, []).append(f)

removed = 0
for key, variants in groups.items():
    if len(variants) <= 1:
        continue
    # 保留一个:优先保留没有 (N) 后缀的原名,否则保留排序第一个;其余删除
    variants.sort(key=lambda x: (pat.match(x) is not None, x))
    for dup in variants[1:]:
        os.remove(os.path.join(folder, dup))
        print("删除重复:", dup)
        removed += 1

left = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
print(f"完成:删除 {removed} 个重复文件,现在文件夹里还有 {left} 个文件。")
