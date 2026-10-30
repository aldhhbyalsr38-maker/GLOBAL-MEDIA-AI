import argparse
from pathlib import Path
from .production import create_production_packs


def main():
    parser = argparse.ArgumentParser(description="Create draft production packs from an editorial plan")
    parser.add_argument("--input", default="output/editorial_plan.json")
    parser.add_argument("--output", default="production")
    args = parser.parse_args()
    files = create_production_packs(Path(args.input), Path(args.output))
    print(f"Created {len(files)} production files in {args.output}")


if __name__ == "__main__":
    main()
