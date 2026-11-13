#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载模型权重到正确位置。

用法（在项目根目录，与 app.py 同级）：
    python download_weights.py

权重文件体积较大（约 780 MB），未纳入 git 仓库，
通过 GitHub Release 分发：v1.0-weights

脚本特性：
- 已存在且大小正确的文件会自动跳过
- 先下载到 .part 临时文件，校验通过后才替换，避免半成品
- 支持断点续传（若目标 .part 已存在则从断点继续）

作者：自动生成
"""

import os
import sys
import urllib.request

# Release 附件地址
BASE_URL = "https://github.com/jully-91/medical-data-visualization/releases/download/v1.0-weights"

# 脚本所在目录 = 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))

# (文件名, 目标路径, 期望字节数)
TARGETS = [
    ("medical_model.pth",
     os.path.join(ROOT, "machine", "medical_model.pth"),
     409170336),
    ("pytorch_model.bin",
     os.path.join(ROOT, "machine", "bert-base-chinese", "pytorch_model.bin"),
     411577189),
]


def _human(n):
    return "%.2f MB" % (n / 1048576.0)


def download_one(name, dest, expected_size):
    """下载单个文件，返回 True 表示成功。"""
    if os.path.exists(dest) and os.path.getsize(dest) == expected_size:
        print("[跳过] %s 已存在且大小正确（%s）" % (name, _human(expected_size)))
        return True

    url = "%s/%s" % (BASE_URL, name)
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    resume_from = os.path.getsize(part) if os.path.exists(part) else 0
    req = urllib.request.Request(url)
    if resume_from:
        req.add_header("Range", "bytes=%d-" % resume_from)
        print("[续传] %s 从 %s 继续" % (name, _human(resume_from)))
    else:
        print("[下载] %s" % url)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            mode = "ab" if resume_from and resp.status == 206 else "wb"
            if mode == "wb":
                resume_from = 0
            done = resume_from
            with open(part, mode) as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    pct = done * 100.0 / expected_size
                    sys.stdout.write("\r  进度 %s / %s (%.1f%%)"
                                     % (_human(done), _human(expected_size), pct))
                    sys.stdout.flush()
        sys.stdout.write("\n")
    except Exception as e:
        print("\n[失败] %s 下载出错：%s" % (name, e))
        return False

    size = os.path.getsize(part)
    if size != expected_size:
        print("[失败] %s 大小不符：%d != %d，已删除临时文件"
              % (name, size, expected_size))
        try:
            os.remove(part)
        except OSError:
            pass
        return False

    os.replace(part, dest)
    print("[完成] %s -> %s" % (name, dest))
    return True


def main():
    print("=" * 60)
    print("医疗疾病数据分析系统 —— 模型权重下载")
    print("=" * 60)

    ok = True
    for name, dest, size in TARGETS:
        ok = download_one(name, dest, size) and ok

    print("-" * 60)
    if ok:
        print("全部就绪，可以启动服务了：python app.py")
    else:
        print("存在失败项，请检查网络后重试；")
        print("也可手动从 Releases 页面下载：")
        print("https://github.com/jully-91/medical-data-visualization/releases/tag/v1.0-weights")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
