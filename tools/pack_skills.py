#!/usr/bin/env python3
"""把 skills/ 下的技能打包成可以上传到 claude.ai 的 ZIP（每个技能一个）。

用法: python3 tools/pack_skills.py [技能名 ...]      # 不带参数则打包全部
输出: dist/<技能名>.zip，内部结构为 <技能名>/SKILL.md 及附属文件

claude.ai 中每个技能相互独立，因此 SKILL.md 里形如 `../其他技能/文件` 的引用，
会把对应文件复制进本技能的包，并改写为同目录路径。
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS, DIST = ROOT / "skills", ROOT / "dist"
REF = re.compile(r"\.\./([\w-]+)/([\w.\-]+)")


def pack(skill_dir: Path) -> Path:
    name = skill_dir.name
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    declared = re.search(r"^name:\s*(\S+)", skill_md, re.M)
    if not declared or declared.group(1) != name:
        raise SystemExit(f"{name}: SKILL.md 的 name 字段必须与文件夹名一致")

    borrowed = {}
    for other, fname in set(REF.findall(skill_md)):
        src = SKILLS / other / fname
        if not src.exists():
            raise SystemExit(f"{name}: 引用的文件不存在 {src}")
        if (skill_dir / fname).exists():
            raise SystemExit(f"{name}: 自身已有 {fname}，与引用的 {other}/{fname} 冲突")
        borrowed[fname] = src
    skill_md = REF.sub(lambda m: m.group(2), skill_md)

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}/SKILL.md", skill_md)
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file() and f.name != "SKILL.md":
                z.write(f, f"{name}/{f.relative_to(skill_dir)}")
        for fname, src in borrowed.items():
            z.write(src, f"{name}/{fname}")
    extra = f"（并入 {', '.join(borrowed)}）" if borrowed else ""
    print(f"  {out.relative_to(ROOT)}{extra}")
    return out


def main():
    names = sys.argv[1:] or sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())
    print("打包技能：")
    for n in names:
        pack(SKILLS / n)


if __name__ == "__main__":
    main()
