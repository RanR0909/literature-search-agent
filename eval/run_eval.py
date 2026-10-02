#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评测脚本:逐题调用 Dify 应用 API,记录回答/时延/是否调用工具/引用来源,产出结果供打分。

用法(先在 Dify 应用「访问 API」拿到以 app- 开头的应用 API Key):
  export DIFY_API_BASE="http://<你的服务器>:<端口>/v1"
  export DIFY_API_KEY="app-xxxxxxxx"
  python eval/run_eval.py

自动记录:latency_s(时延)、tool_called(是否触发工具)、has_citation(是否带知识库引用)。
需人工打分的维度(文献真实性/链接有效/引用准确/任务完成)在结果里留空字段,跑完逐条填。
零第三方依赖。
"""
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE = os.environ.get("DIFY_API_BASE", "").rstrip("/")
KEY = os.environ.get("DIFY_API_KEY", "")
HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "golden_questions.jsonl"
OUT_DIR = HERE / "results"


def ask(query: str, timeout: int = 120):
    """调用 Dify chat-messages(blocking)。返回 (data, latency_s, error)。"""
    url = f"{BASE}/chat-messages"
    body = json.dumps({
        "inputs": {}, "query": query, "response_mode": "blocking", "user": "eval-bot",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
    })
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), round(time.time() - t, 2), None
    except urllib.error.HTTPError as e:
        return None, round(time.time() - t, 2), f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}"
    except Exception as e:
        return None, round(time.time() - t, 2), str(e)


def detect(data: dict):
    """从 Dify 返回里粗判是否调用了工具、是否带引用。"""
    if not data:
        return False, False
    meta = data.get("metadata", {}) or {}
    has_citation = bool(meta.get("retriever_resources"))
    tool_called = False
    for th in data.get("agent_thoughts", []) or []:
        if th.get("tool"):
            tool_called = True
            break
    return tool_called, has_citation


def main():
    if not BASE or not KEY:
        raise SystemExit("请先设置环境变量 DIFY_API_BASE 和 DIFY_API_KEY")
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    with out.open("w", encoding="utf-8") as fo:
        for q in rows:
            data, latency, err = ask(q["question"])
            tool_called, has_citation = detect(data)
            answer = (data or {}).get("answer", "") if not err else ""
            rec = {
                "id": q["id"],
                "dimension": q.get("dimension", []),
                "question": q["question"],
                "expected_route": q.get("expected_route"),
                "expected_behavior": q.get("expected_behavior"),
                # —— 自动指标 ——
                "latency_s": latency,
                "tool_called": tool_called,
                "has_citation": has_citation,
                "error": err,
                "answer": answer,
                # —— 人工打分(跑完逐条填)——
                "grade_route_correct": None,      # 意图路由对不对 0/1
                "grade_refs_real": None,          # 文献真实、链接可打开 0/1
                "grade_citation_accurate": None,  # 引用确来自知识库 0/1
                "grade_honest_degradation": None, # 无结果时是否诚实 0/1/NA
                "grade_task_completion": None,    # 任务完成 1-5
                "note": "",
            }
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            flag = "ERR" if err else ("TOOL" if tool_called else ("KB" if has_citation else "-"))
            print(f"[{q['id']}] {latency}s {flag}  {q['question'][:30]}")
    print("\n结果已写入:", out)
    print("请打开逐条填写 grade_* 字段,再汇总各指标。")


if __name__ == "__main__":
    main()
