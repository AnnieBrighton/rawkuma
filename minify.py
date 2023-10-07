#!/usr/bin/env python3

import os
import re
import shutil
import sys
import asyncio
import aiofiles

def_dest = "/tmp/rawkuma/dest"
LIMITS = 20


async def minify(dest, current_dir, file):
    """HTML/CSS/JavaScriptを圧縮する

    Args:
        dest (str): 転送先
        current_dir (str): ファイルのパス
        file (str): ソースファイル
    """
    extention = file.split(".")[-1]  # 拡張子
    src_path = os.path.join(current_dir, file)
    dst_path = os.path.join(dest, current_dir, file)

    async with aiofiles.open(src_path, mode="r", encoding="utf_8") as f:
        s0 = await f.readlines()

    if extention == "html":
        s1 = "".join([s.strip() for s in s0])  # 各行の前後の空白を削除
        s2 = re.sub("/\*.*?\*/", "", s1)  # コメントの削除
        s0 = re.sub("<!--.*?-->", "", s2)  # コメントの削除
    elif extention == "css":
        s1 = "".join([s.strip() for s in s0])  # 各行の前後の空白を削除
        s2 = re.sub("/\*.*?\*/", "", s1)  # コメントの削除
        s3 = re.sub(": +?", ":", s2)  # セミコロン後の空白を削除
        s0 = re.sub(" +?{", "{", s3)  # '{'前の空白を削除
    elif extention == "js":
        s1 = [s.split("//")[0] for s in s0]  # 1行コメント(//以降)を削除
        s2 = "".join([s.strip() for s in s1])  # 各行の前後の空白を削除
        s0 = re.sub("/\*.*?\*/", "", s2)  # コメント(/* */)の削除

    async with aiofiles.open(dst_path, mode="w", encoding="utf_8") as f:
        await f.write(s0)


async def main(src, dest, limit):
    sem = asyncio.Semaphore(limit)

    for current_dir, sub_dirs, files_list in os.walk(src):
        for subdir in sub_dirs:
            os.makedirs(os.path.join(dest, current_dir, subdir), exist_ok=True)

        async def call(file):
            async with sem:
                return await minify(dest, current_dir, file)

        await asyncio.gather(*[call(file) for file in files_list])


if __name__ == "__main__":
    if len(sys.argv) > 3:
        asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
    elif len(sys.argv) > 2:
        asyncio.run(main(sys.argv[1], sys.argv[2], LIMITS))
    elif len(sys.argv) > 1:
        asyncio.run(main(sys.argv[1], def_dest, LIMITS))
