# -*- coding: utf-8 -*-
"""
基线自动更新器（story-learn 流水线的第二环）。
读取 analyze-corpus.py 的 JSON 输出，合并进 genre-baselines.md 与 tropes.md。
用法: python update-baselines.py <stats.json> [--dir <story-platform目录>]
默认在脚本同级的 ../references/ 下写 genre-baselines.md 与 tropes.md；--dir 可覆盖为 skill 根目录。
幂等：重复运行同一 JSON 结果一致；curated 文本（变体/警报/技法）不会被覆盖。
"""
import os, re, sys, json, datetime

def read(p):
    return open(p, encoding='utf-8').read()

def write(p, text):
    open(p, 'w', encoding='utf-8').write(text)

def main():
    stats = json.load(open(sys.argv[1], encoding='utf-8'))
    plat = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for a in sys.argv[2:]:
        if a.startswith('--dir='): plat = a.split('=', 1)[1]
    today = datetime.date.today().isoformat()
    n = stats['样本量']
    changes = []

    # ---------- genre-baselines.md ----------
    gb = os.path.join(plat, 'references', 'genre-baselines.md')
    if os.path.exists(gb):
        t = read(gb)
        # 1. 来源行
        t = re.sub(r'> 来源：.*', f'> 来源：analyze-corpus.py 对 {n} 篇语料的统计（{today}）+ 定向精读。', t, count=1)
        changes.append('来源行更新')
        # 2. 通用数据表
        fl = stats.get('导语长度') or {}
        sec = stats.get('分节') or {}
        end = stats.get('结尾类型') or {}
        genres = stats.get('题材分布') or {}
        top3 = [f"{g} {c}%" for g, c in list(genres.items())[:4]]
        dl = f"{fl.get('均值','?')}~{fl.get('P75','?')}" if fl else '?'
        med = sec.get('中位') or 9
        if med >= 15:
            sec_rule = f"完整盐选短篇按 **{max(15, med-3)}~{med+3} 节** 规划（签约范文实测中位 {med}）；知乎问答短回答 9~11 节"
        else:
            # 知乎问答语料中位普遍 9~11，若直接覆盖会把盐选签约短篇的 15~21 节规则打回——只降不升，保留签约文口径
            sec_rule = f"知乎问答短回答按 **9~11 节** 规划（本次语料中位 {med}）；盐选签约完整短篇仍按 **15~21 节**（签约范文实测中位 18）"
        rows = [
            "| 指标 | 数据 | 转化规则 |",
            "|---|---|---|",
            f"| 导语长度 | 均值 {fl.get('均值','?')} / 中位 {fl.get('中位','?')} / P75 {fl.get('P75','?')} 字 | **导语黄金区间 15~28 字**。超 30 字 = 太啰嗦；短于 10 字 = 悬念不足 |",
            f"| 分节数 | 中位 {med} 节 | {sec_rule} |",
            "| 结尾类型 | " + " ｜ ".join(f"{k} {v}%" for k, v in list(end.items())[:4]) + " | **短句收尾是常态**（\"小祖宗。\"\"嗯，真乖！\"）；狠话金句是加分项不是必选项 |",
            f"| 题材热度 | {' ｜ '.join(top3)} | 家庭+情感类是盐选基本盘；悬疑是稳定第二梯队 |",
        ]
        new_table = "\n".join(rows) + "\n"
        # 用行尾 \n 锚定，避免 markdown 单元格内多个 | 导致的错切
        t = re.sub(r'\| 指标 \| 数据 \| 转化规则 \|.*?\| 题材热度 \|.*?\n', new_table, t, count=1, flags=re.S)
        changes.append('通用数据表更新')
        # 3. 样本区块（可重复替换）
        samples = stats.get('各题材导语样本') or {}
        block = [f"\n## 最新语料导语样本（{today}，{n} 篇）\n"]
        for g in ['现实情感','悬疑/犯罪','都市/职场','言情/情感','家庭/亲情','灵异/玄幻','校园']:
            ss = samples.get(g) or []
            if not ss: continue
            block.append(f"\n**{g}**")
            for p in ss[:4]: block.append(f"- {p[:64]}")
        block.append("")
        new_sec = "\n".join(block)
        # 区块可能在文件中段（后有 ## 标题）也可能在文件末尾（EOF）——\Z 兜底，避免重复追加
        t2 = re.sub(r'\n## 最新语料导语样本（.*?）\n.*?(?=\n## |\Z)', '\n' + new_sec, t, count=1, flags=re.S)
        if t2 == t:
            t = t.rstrip() + '\n' + new_sec
            changes.append('新增语料样本区')
        else:
            t = t2
        write(gb, t)
        changes.append('导语样本更新')
    else:
        print('[SKIP] references/genre-baselines.md 不存在')

    # ---------- tropes.md ----------
    tp = os.path.join(plat, 'references', 'tropes.md')
    if os.path.exists(tp):
        t = read(tp)
        tropes = stats.get('母题词频') or {}
        line = " ｜ ".join(f"{k} {v}" for k, v in tropes.items())
        t = re.sub(r'## 母题词频（.*?）\n\n.*?\n\n', f'## 母题词频（{today}，{n} 篇）\n\n{line}\n\n', t, count=1, flags=re.S)
        write(tp, t)
        changes.append('母题词频更新')
    else:
        print('[SKIP] references/tropes.md 不存在')

    print(f"✅ 基线已更新（{n} 篇，{today}）：{', '.join(changes)}")

if __name__ == '__main__':
    main()
