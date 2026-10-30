import argparse
import json
from pathlib import Path
from .research import build_plan, write_outputs

def main():
    parser = argparse.ArgumentParser(description="GLOBAL MEDIA AI research cycle")
    parser.add_argument("--config", default="config/settings.json")
    parser.add_argument("--output", default="output")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    plan = build_plan(config)
    json_path, md_path = write_outputs(plan, Path(args.output))
    print(f"Selected {len(plan['topics'])} topics")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    if not plan["topics"]:
        raise SystemExit("No topics collected. Check feed availability or try again later.")

if __name__ == "__main__":
    main()
