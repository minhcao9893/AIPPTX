"""
main.py — CLI Entry Point
===========================
Full pipeline: input.json → sanitize → AI plan → build → output.pptx

Usage:
    python main.py --input input.json
    python main.py --input input.json --template my_template.pptx
    python main.py --only-sanitize --input input.json
    python main.py --only-build --input input.json

Steps:
    1. sanitizer.py  → skeleton.json + mask_map.json  (local, fast)
    2. ai_planner.py → layout_plan.json               (calls Claude API w/ skeleton only)
    3. builder.py    → output.pptx                    (local, unmask happens here)
"""

import argparse
import json
import sys
import os


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="ai-pptx: Generate presentations from data without exposing data to AI."
    )
    parser.add_argument("--input",    default="input.json",
                        help="Path to input JSON file (default: input.json)")
    parser.add_argument("--template", default=None,
                        help="Path to .pptx template file (optional)")
    parser.add_argument("--output",   default="output.pptx",
                        help="Output .pptx path (default: output.pptx)")
    parser.add_argument("--only-sanitize", action="store_true",
                        help="Run sanitize step only, then stop")
    parser.add_argument("--only-build",    action="store_true",
                        help="Skip sanitize+plan, build from existing JSON files")
    args = parser.parse_args()

    # ── Step 1: Sanitize ───────────────────────────────────────────────────
    if not args.only_build:
        print("🔒 Step 1: Sanitizing data…")
        from .sanitizer import sanitize, build_skeleton_metadata

        raw_data = load_json(args.input)
        skeleton, name_map = sanitize(raw_data)
        skeleton = build_skeleton_metadata(skeleton)

        save_json(skeleton,   "skeleton.json")
        save_json(name_map,   "name_map.json")
        print(f"   ✅ {len(name_map)} names masked → skeleton.json saved")
        if name_map:
            for alias, original in name_map.items():
                print(f"      {alias:20s} → {original}")
        print(f"   ⚠️  name_map.json PRIVATE — never share")
        mask_map = name_map  # alias for builder compatibility

        if args.only_sanitize:
            print("\nDone (sanitize only).")
            return

        # ── Step 2: AI Layout Planning ─────────────────────────────────────
        print("\n📡 Step 2: AI layout planning (skeleton only, no real data)…")
        from .ai_planner import plan_layout

        layout_plan = plan_layout(skeleton)
        save_json(layout_plan, "layout_plan.json")
        n = len(layout_plan.get("slides", []))
        print(f"   ✅ {n} slide layout(s) planned → layout_plan.json saved")

    else:
        # Load intermediate files from previous run
        print("⚡ --only-build: loading existing skeleton/mask/plan files…")
        if not all(os.path.exists(f) for f in
                   ["skeleton.json", "mask_map.json", "layout_plan.json"]):
            print("❌ Missing one of: skeleton.json, mask_map.json, layout_plan.json")
            print("   Run without --only-build first to generate these files.")
            sys.exit(1)

        raw_data    = load_json(args.input)
        mask_map    = load_json("name_map.json") if os.path.exists("name_map.json") else \
                      load_json("mask_map.json") if os.path.exists("mask_map.json") else {}
        scale_map   = {}
        layout_plan = load_json("layout_plan.json")

    # ── Step 3: Build PPTX ────────────────────────────────────────────────
    print("\n🎨 Step 3: Building PPTX (data unmasked locally)…")
    from .builder import build

    build(layout_plan, mask_map, raw_data,
          scale_map={},
          template_path=args.template,
          output_path=args.output)


if __name__ == "__main__":
    main()
