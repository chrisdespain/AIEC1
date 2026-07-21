"""Activity 1: RAGAS evaluation with cost analysis.

Run this script to compare a Fireworks AI RAG pipeline against an OpenAI
``gpt-4.1-mini`` equivalent. Results are printed to the console and saved to
``activity_1_results.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from app.evaluate import compare_providers

load_dotenv(override=True)
os.environ.setdefault("LANGSMITH_TRACING", "true")


def main():
    pdf_path = "data/cat-health-guide.pdf"

    # Questions drawn from the 2021 AAHA/AAFP Feline Life Stage Guidelines PDF.
    questions = [
        "What are the four distinct age-related life stages for cats described in the 2021 AAHA/AAFP Feline Life Stage Guidelines?",
        "What body condition score is considered obese in cats, and what score is considered overweight?",
        "Why is neutering associated with obesity risk in cats?",
        "What are the recommended core vaccinations for kittens according to the guidelines?",
        "How is the daily energy requirement (DER) calculated for a young, healthy adult cat?",
    ]

    # Reference (ground-truth) answers for answer-correctness/context-recall metrics.
    references = [
        (
            "The 2021 AAHA/AAFP Feline Life Stage Guidelines divide a cat's lifespan "
            "into five stages: kitten, young adult, mature adult, senior, and end-of-life."
        ),
        (
            "A body condition score (BCS) of 6/9 or 7/9 is considered overweight, "
            "and a BCS greater than or equal to 8/9 is considered obese."
        ),
        (
            "Neutering is a risk factor for obesity in cats, especially in males, "
            "so dietary energy restriction may be appropriate to prevent weight gain."
        ),
        (
            "Core vaccinations for kittens include rabies virus, feline herpesvirus type 1, "
            "feline calicivirus, and feline panleukopenia virus. Feline leukemia virus is "
            "considered core for kittens, and a booster is recommended at 6 months of age."
        ),
        (
            "Daily energy requirement (DER) is calculated by multiplying resting energy "
            "requirement (RER = 30 x body weight in kg + 70) by a needs factor; the needs "
            "factor for young, healthy adult cats is 1."
        ),
    ]

    results = compare_providers(questions, references=references, pdf_path=pdf_path)

    # Pretty-print a summary.
    print("=" * 80)
    print("Activity 1: RAGAS Evaluation with Cost Analysis")
    print("=" * 80)

    for provider in ("fireworks", "openai"):
        print(f"\n--- {provider.upper()} ---")
        responses = results[f"{provider}_responses"]
        for idx, r in enumerate(responses, 1):
            print(f"\nQ{idx}: {r.question}")
            print(f"Answer: {r.answer[:250]}{'...' if len(r.answer) > 250 else ''}")
            print(
                f"Latency: {r.latency_seconds:.2f}s | "
                f"Input tokens: {r.input_tokens} | Output tokens: {r.output_tokens} | "
                f"Embedding tokens: {r.embedding_tokens} | "
                f"Est. cost: ${r.estimated_cost_usd:.6f}"
            )

    print("\n--- Estimated total cost per provider ---")
    print(f"Fireworks: ${results['fireworks_cost_usd']:.6f}")
    print(f"OpenAI:    ${results['openai_cost_usd']:.6f}")

    print("\n--- RAGAS scores ---")
    print("Fireworks:")
    print(results["fireworks_eval"])
    print("\nOpenAI:")
    print(results["openai_eval"])

    # Persist results.
    serializable = {
        "fireworks_cost_usd": results["fireworks_cost_usd"],
        "openai_cost_usd": results["openai_cost_usd"],
        "fireworks_responses": [
            {
                "question": r.question,
                "answer": r.answer,
                "contexts": r.contexts,
                "latency_seconds": r.latency_seconds,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "embedding_tokens": r.embedding_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
            }
            for r in results["fireworks_responses"]
        ],
        "openai_responses": [
            {
                "question": r.question,
                "answer": r.answer,
                "contexts": r.contexts,
                "latency_seconds": r.latency_seconds,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "embedding_tokens": r.embedding_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
            }
            for r in results["openai_responses"]
        ],
        "fireworks_scores": results["fireworks_eval"].to_pandas().to_dict(orient="records"),
        "openai_scores": results["openai_eval"].to_pandas().to_dict(orient="records"),
    }

    out_path = Path("activity_1_results.json")
    out_path.write_text(json.dumps(serializable, indent=2, default=str))
    print(f"\nResults saved to {out_path.resolve()}")


if __name__ == "__main__":
    main()
