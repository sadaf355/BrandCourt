"""Score predictions against data/sample/glowserum_40_posts.jsonl.
Predictions JSONL: {"id":"GC-001","predicted_findings":["wrong_number"]}
"""
import argparse, json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_DATA=ROOT/'data'/'sample'/'glowserum_40_posts.jsonl'

def load(path): return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
def score(gold, predictions):
    pred_by_id={r['id']:set(r.get('predicted_findings',[])) for r in predictions}
    labels=sorted({label for row in gold for label in row.get('expected_findings',[])} | {label for row in predictions for label in row.get('predicted_findings',[])})
    report={}; micro=[0,0,0]
    for label in labels:
        tp=fp=fn=0
        for row in gold:
            expected=set(row.get('expected_findings',[])); predicted=pred_by_id.get(row['id'],set())
            tp += int(label in expected and label in predicted)
            fp += int(label not in expected and label in predicted)
            fn += int(label in expected and label not in predicted)
        precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
        report[label]={'tp':tp,'fp':fp,'fn':fn,'precision':round(precision,4),'recall':round(recall,4)}
        micro=[micro[0]+tp,micro[1]+fp,micro[2]+fn]
    tp,fp,fn=micro
    return {'examples':len(gold),'predictions_supplied':len(predictions),'micro_precision':round(tp/(tp+fp),4) if tp+fp else 0.0,'micro_recall':round(tp/(tp+fn),4) if tp+fn else 0.0,'by_label':report,'note':'Missing prediction rows count as no predicted findings. This script scores supplied predictions; it does not fabricate model results.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gold',default=str(DEFAULT_DATA));p.add_argument('--predictions',required=True);p.add_argument('--out');a=p.parse_args()
    result=score(load(a.gold),load(a.predictions)); output=json.dumps(result,indent=2)
    if a.out: Path(a.out).write_text(output+'\n',encoding='utf-8')
    print(output)
