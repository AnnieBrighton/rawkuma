#!/usr/bin/env python3

import os
import re
import shutil
import sys

dest = "dest"

def minify(src_path, dest_path):
    """HTML/CSS/JavaScriptを圧縮する

    Args:
        src_path (str): 圧縮したいファイルのパス
        dest_path (str): 圧縮後に保存するパス
    """
    extention = src_path.split(".")[-1] # 拡張子

    with open(src_path, encoding="utf_8") as f:
        s0 = f.readlines()

    if extention=="html":
        s1 = "".join([s.strip() for s in s0]) # 各行の前後の空白を削除
        s2 = re.sub('/\*.*?\*/', '', s1) # コメントの削除
        s9 = re.sub('<!--.*?-->', '', s2) # コメントの削除
    elif extention=="css":
        s1 = "".join([s.strip() for s in s0]) # 各行の前後の空白を削除
        s2 = re.sub('/\*.*?\*/', '', s1) # コメントの削除
        s3 = re.sub(': +?', ':', s2) # セミコロン後の空白を削除
        s9 = re.sub(' +?{', '{', s3) # '{'前の空白を削除
    elif extention=="js":
        s1 = [s.split("//")[0] for s in s0] # 1行コメント(//以降)を削除
        s2 = "".join([s.strip() for s in s1]) # 各行の前後の空白を削除
        s9 = re.sub('/\*.*?\*/', '', s2) # コメント(/* */)の削除

    with open(dest_path, mode='w', encoding="utf_8") as f:
        f.write(s9)

def main(src):
    for current_dir, sub_dirs, files_list in os.walk(src):
        for subdir in sub_dirs:
            os.makedirs(os.path.join(dest, current_dir, subdir), exist_ok=True)

        for file in files_list:
            extention = file.split(".")[-1] # 拡張子
            src_file_path = os.path.join(current_dir, file)
            dst_file_path = os.path.join(dest, current_dir, file)
            if extention in ["html", "css", "js"]:
                minify(src_file_path, dst_file_path)
            else:
                shutil.copy2(src_file_path, dst_file_path)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
