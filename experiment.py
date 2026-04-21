
"""
experiment.py — Run red-team experiments against the target medical AI.

Usage
-----
# Run all 15 attack types:
    python experiment.py

# Run specific attack types:
    python experiment.py --attacks direct role_play cot_hijacking

# Run all attacks, 3 refinement rounds per prompt:
    python experiment.py --max-iters 3

# Limit to first N seed prompts per attack type (useful for quick smoke-tests):
    python experiment.py --max-prompts 3

Environment variables (.env file or shell export)
--------------------------------------------------
    MISTRAL_API_KEY   — your Mistral API key (attacker model)
    # or
    GEMINI_API_KEY    — your Gemini API key (swap attacker class below)
"""

import os
import json
import argparse
from dotenv import load_dotenv

from attacker import AttackerModel          # swap to GeminiAttacker if preferred
from attack import generate_attack_prompts, adaptive_attack_loop
from system_prompts import SYSTEM_PROMPTS
from target import TargetModel

load_dotenv()


# ──────────────────────────────────────────────────────────────────────────────
# CLIp
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Medical AI red-team experiment runner")
    parser.add_argument(
        "--attacks",
        nargs="+",
        choices=list(SYSTEM_PROMPTS.keys()),
        default=list(SYSTEM_PROMPTS.keys()),
        help="Attack types to run (default: all)",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=5,
        help="Max refinement rounds per prompt (default: 5)",
    )
    parser.add_argument(
        "--max-prompts",
        type=int,
        default=None,
        help="Max seed prompts per attack type — useful for quick tests (default: all 15)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to write JSON result files (default: ./results)",
    )
    parser.add_argument(
        "--attacker-base-url",
        type=str,
        default="http://localhost:4141/v1/chat/completions",
        help="OpenAI-compatible endpoint for the attacker model",
    )
    parser.add_argument(
        "--attacker-model",
        type=str,
        default="gpt-5-mini",
        help="Attacker model name",
    )
    parser.add_argument(
        "--judge-base-url",
        type=str,
        default="http://localhost:4141/v1/chat/completions",
        help="OpenAI-compatible endpoint for judge models",
    )
    parser.add_argument(
        "--judge-models",
        nargs=3,
        metavar=("JUDGE1", "JUDGE2", "JUDGE3"),
        default=["gemini-3-flash-preview", "gpt-4o-mini", "gpt-5-mini"],
        help="Exactly three judge model names for majority voting",
    )
    parser.add_argument(
        "--target-base-url",
        type=str,
        default="http://localhost:8000/v1/chat/completions",
        help="OpenAI-compatible endpoint for the target model",
    )
    parser.add_argument(
        "--target-model",
        type=str,
        default="biomistral/biomistral-7b",
        help="Target model name",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # --- Initialise models ---------------------------------------------------
    attacker = AttackerModel(
        base_url=args.attacker_base_url,
        model_name=args.attacker_model,
    )
    judges = [
        AttackerModel(base_url=args.judge_base_url, model_name=model_name)
        for model_name in args.judge_models
    ]
    target = TargetModel(
        base_url=args.target_base_url,
        model_name=args.target_model,
    )

    print("\nJudge ensemble:")
    for idx, judge_name in enumerate(args.judge_models, 1):
        print(f"  Judge {idx}: {judge_name}")

    summary = {}   # attack_type → {total, success, failed}

    # --- Run each attack type ------------------------------------------------
    for attack_type in args.attacks:
        print(f"\n{'='*60}")
        print(f"ATTACK TYPE: {attack_type.upper()}")
        print(f"{'='*60}")

        # 1. Generate seed prompts via the attacker model
        seed_prompts = generate_attack_prompts(attacker, attack_type)

        if args.max_prompts:
            seed_prompts = seed_prompts[: args.max_prompts]

        print(f"  Seed prompts generated: {len(seed_prompts)}")

        results = []

        # 2. Run the adaptive loop for each seed prompt
        for idx, prompt in enumerate(seed_prompts, 1):
            # pace ourselves: pause briefly every 10 requests to avoid rate limits
            # if idx % 5 == 0:
            #     import time
            #     time.sleep(30)

            print(f"\n  [{idx}/{len(seed_prompts)}] {prompt[:80]}{'…' if len(prompt) > 80 else ''}")

            result = adaptive_attack_loop(
                attacker=attacker,
                target=target,
                judges=judges,
                attack_type=attack_type,
                initial_prompt=prompt,
                max_iters=args.max_iters,
            )

            status_icon = "✅ SUCCESS" if result["status"] == "SUCCESS" else "❌ FAILED"
            steps_taken = len(result["conversation"])
            print(f"     {status_icon} after {steps_taken} step(s)")

            results.append(result)

        # 3. Save results for this attack type
        out_path = os.path.join(args.output_dir, f"{attack_type}_results_biomistral-gpt3.5.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"\n  Results saved → {out_path}")

        # 4. Accumulate summary stats
        successes = sum(1 for r in results if r["status"] == "SUCCESS")
        summary[attack_type] = {
            "total":   len(results),
            "success": successes,
            "failed":  len(results) - successes,
            "success_rate": f"{successes / len(results) * 100:.1f}%" if results else "N/A",
        }

    # --- Print overall summary -----------------------------------------------
    print(f"\n{'='*60}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"{'Attack Type':<25} {'Total':>6} {'Success':>8} {'Failed':>7} {'Rate':>8}")
    print("-" * 58)
    for attack_type, stats in summary.items():
        print(
            f"{attack_type:<25} {stats['total']:>6} {stats['success']:>8} "
            f"{stats['failed']:>7} {stats['success_rate']:>8}"
        )

    # Save summary
    summary_path = os.path.join(args.output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=4)
    print(f"\nFull summary saved → {summary_path}")


if __name__ == "__main__":
    main()