# -*- coding: utf-8 -*-
"""
盐选范文库分析器（story-learn 流水线的第一环）。
用法:
  python analyze-corpus.py <语料目录> [--limit=N] [--json <输出.json>]
输出: 题材分布 / 导语长度 / 分节 / 结尾类型 / 母题词频 / 各题材导语样本
      --json 时输出结构化结果供 update-baselines.py 使用
"""
import os, re, sys, json, collections, statistics, random

def clean(text):
    text = re.sub(r'&emsp;|&nbsp;|<br\s*/?>|</?[a-zA-Z]+>', ' ', text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # 丢弃知乎问题标题/标签行（以 # 开头），避免污染导语样本与长度统计
    lines = [l for l in lines if not l.startswith('#')]
    return [l for l in lines if len(l) > 1]

SKIP_WORDS = ['原文地址','备案号','本文搬运来自','收藏于','全文完','完','.','本文来自','转载','上一篇','下一篇','打赏','点赞']

def first_para(paras):
    for p in paras:
        if re.search(r'[。！？!?]', p) and 8 < len(p) < 200:
            return p
    return ''

def last_para(paras):
    for p in reversed(paras):
        if len(p) < 4: continue
        if any(w in p for w in SKIP_WORDS): continue
        if re.match(r'^\d+$', p): continue
        return p
    return ''

def section_count(text):
    t = re.sub(r'&emsp;|&nbsp;|<br\s*/?>', ' ', text)
    lines = [l.strip() for l in t.splitlines()]
    return sum(1 for l in lines if re.fullmatch(r'(?:0?[1-9]|[1-9][0-9])', l))

GENRES = {
    '现实情感': ['出轨','劈腿','绿','离婚','前妻','前夫','彩礼','相亲','婆婆','岳母','丈母娘','亲戚','老婆','老公','婚姻','赡养','遗产','被绿','凤凰男','扶弟魔','重男轻女','闪婚','渣男'],
    '家庭/亲情': ['父亲','母亲','爸爸','妈妈','儿子','女儿','爷爷','奶奶','哥哥','弟弟','姐姐','妹妹','孩子','舅舅','姑','养女','继父','后妈','姥姥','外公','爹','娘'],
    '悬疑/犯罪': ['杀人','尸体','命案','凶案','警察','刑警','法医','侦探','失踪','死亡','碎尸','绑架','犯罪','尸','嫌疑','案子','凶手','遗书','报警','刑侦','悬疑','谋杀','凶杀'],
    '言情/情感': ['初恋','暗恋','男朋友','女朋友','恋爱','分手','喜欢','心动','前任','复合','结婚','未婚夫','未婚妻','穿书','追妻','白月光','朱砂痣','青梅竹马','先婚后爱','甜宠','霸总','总裁','心上人'],
    '都市/职场': ['公司','老板','同事','职场','裁员','面试','上班','领导','部门','工资','加班','创业','离职','上班族','秘书','实习','期权','甲方','乙方','豪门','项目','客户'],
    '灵异/玄幻': ['鬼','僵尸','重生','穿越','系统','修仙','坟','阴间','轮回','诅咒','灵异','阴婚','收尸','妖','仙','剑修','魔尊','前世','地府','冥婚','古言','法师','蛊'],
    '校园': ['高中','大学','同学','老师','宿舍','高考','班长','同桌','校花','学弟','学姐','校霸','转学','军训'],
}

TROPES = {
    '背叛/出轨': ['出轨','劈腿','被绿','小三','外遇','背叛'],
    '家庭偏心/牺牲': ['偏心','继母','继妹','重男轻女','婆婆','彩礼','捐肾','赡养','私生子'],
    '职场背锅/恶人': ['老板','同事','裁员','辞职','背锅','上司','部门','加班'],
    '重生/穿越/系统': ['重生','穿越','系统','金手指'],
    '悬疑/犯罪': ['杀人','尸体','失踪','绑架','命案','碎尸','警察','刑警'],
    '情感错过/前任': ['前男友','前女友','初恋','暗恋','相亲','分手'],
    '复仇/反杀': ['报复','复仇','算计','教训','打脸'],
}

def classify(title, paras):
    blob = title + ' ' + ' '.join(paras[:8])
    scores = {g: sum(1 for kw in kws if kw in blob) for g, kws in GENRES.items()}
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else '其他'

def ending_type(last):
    if len(last) <= 14:
        return '短句/称呼'
    if any(k in last for k in ['报应','罪有应得','活该','教训','笑','冷笑','应得的']):
        return '狠话/因果'
    if any(k in last for k in ['生活','人生','世界','日子','未来','明天','希望','路还长']):
        return '哲思/展望'
    if last.startswith('「') or last.startswith('“') or '说：' in last or last.endswith('」') or last.endswith('”'):
        return '对话'
    if any(k in last for k in ['灯','雨','风','月亮','阳光','影','烟','账','路','巷','草','雪']):
        return '意象'
    return '平淡'

def main():
    root = sys.argv[1]
    limit, json_path = None, None
    for a in sys.argv[2:]:
        if a.startswith('--limit='): limit = int(a.split('=')[1])
        if a.startswith('--json='): json_path = a.split('=', 1)[1]
    files = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith('.md'): files.append(os.path.join(dp, fn))
    # 抽样必须随机（固定种子可复现），避免按目录顺序取前 N 引入偏倚
    if limit and limit < len(files): files = random.Random(42).sample(files, limit)

    stats = collections.Counter()
    first_lens, sec_counts, endings, tropes = [], [], collections.Counter(), collections.Counter()
    fp_by_genre = collections.defaultdict(list)
    lp_by_genre = collections.defaultdict(list)

    for f in files:
        try: text = open(f, encoding='utf-8', errors='ignore').read()
        except Exception: continue
        paras = clean(text)
        if len(paras) < 10: continue
        title = os.path.basename(f).replace('.md', '')
        g = classify(title, paras)
        stats[g] += 1
        fp, lp = first_para(paras), last_para(paras)
        if fp: first_lens.append(len(fp))
        sec_counts.append(section_count(text))
        endings[ending_type(lp)] += 1
        if len(fp_by_genre[g]) < 8 and fp: fp_by_genre[g].append(fp)
        if len(lp_by_genre[g]) < 6 and lp: lp_by_genre[g].append(lp)
        body = title + ' ' + ' '.join(paras[:15])
        for trope, kws in TROPES.items():
            if any(kw in body for kw in kws): tropes[trope] += 1

    total = max(sum(stats.values()), 1)
    result = {
        '样本量': total,
        '语料目录': root,
        # JSON 里存百分比（rounded），避免下游把计数当百分比用
        '题材分布': {g: round(c * 100 / total) for g, c in stats.most_common()},
        '导语长度': None,
        '分节': None,
        '结尾类型': {t: round(c * 100 / total) for t, c in endings.most_common()},
        '母题词频': dict(tropes.most_common()),
        '各题材导语样本': {g: v[:6] for g, v in fp_by_genre.items()},
        '各题材结尾样本': {g: v[:4] for g, v in lp_by_genre.items()},
    }
    if first_lens:
        fl = sorted(first_lens)
        result['导语长度'] = {'均值': round(statistics.mean(first_lens)), '中位': int(statistics.median(first_lens)),
                             'P25': fl[len(fl)//4], 'P75': fl[3*len(fl)//4]}
    if sec_counts:
        result['分节'] = {'均值': round(statistics.mean(sec_counts),1), '中位': int(statistics.median(sec_counts)), '最多': max(sec_counts)}

    if json_path:
        with open(json_path, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print(f"JSON 已写入 {json_path}")
    print(f"== 样本量: {total} 篇 ==")
    print("\n== 题材分布 ==")
    for g, c in stats.most_common(): print(f"  {g}: {c} ({c*100//total}%)")
    if result['导语长度']: print(f"\n== 导语长度: {result['导语长度']} ==")
    if result['分节']: print(f"== 分节: {result['分节']} ==")
    print("\n== 结尾类型 ==")
    for t, c in endings.most_common(): print(f"  {t}: {c} ({c*100//total}%)")
    print("\n== 母题词频 ==")
    for t, c in tropes.most_common(): print(f"  {t}: {c}")
    print("\n== 各题材导语样本 ==")
    for g in ['现实情感','悬疑/犯罪','都市/职场','言情/情感','家庭/亲情']:
        print(f"\n--- {g} ---")
        for p in fp_by_genre.get(g, [])[:5]: print("  ·", p[:70])

if __name__ == '__main__':
    main()
