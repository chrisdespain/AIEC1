import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_case(question: str) -> tuple[str, list[str]]:
    from agent import stream_response

    answer = ""
    contexts = []
    async for chunk in stream_response(question, str(uuid4())):
        if not chunk.startswith("data: "):
            continue
        try:
            ev = json.loads(chunk[6:].strip())
        except json.JSONDecodeError:
            continue
        if ev["type"] == "result":
            answer = ev["text"]
        elif ev["type"] == "tool" and ev["name"] in ("Read", "Glob", "Grep"):
            contexts.append(ev["input"])
    return answer, contexts

async def main():
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness, context_precision

    test_path = Path(__file__).parent / "test_cases.json"
    if not test_path.exists():
        print("test_cases.json not found. Run: uv run eval/generate_testset.py")
        sys.exit(1)

    cases = json.loads(test_path.read_text())
    rows = []

    for i, case in enumerate(cases):
        question = case.get("question") or case.get("user_input") or ""
        ground_truth = case.get("ground_truth") or case.get("reference") or ""
        if not question:
            continue
        print(f"[{i+1}/{len(cases)}] {question[:70]}...")
        answer, contexts = await run_case(question)
        rows.append({
            "question": question,
            "answer": answer,
            "contexts": contexts or ["(no file context retrieved)"],
            "ground_truth": ground_truth,
        })

    dataset = Dataset.from_list(rows)
    results = evaluate(dataset, metrics=[answer_relevancy, faithfulness, context_precision])

    print("\n=== RAGAS Results ===")
    print(results)

    report = Path(__file__).parent / "eval_report.json"
    report.write_text(json.dumps(
        results.to_pandas().to_dict(orient="records"), indent=2, default=str
    ))
    print(f"\nReport saved to {report}")

if __name__ == "__main__":
    asyncio.run(main())
