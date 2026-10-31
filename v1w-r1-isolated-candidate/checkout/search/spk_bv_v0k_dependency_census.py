#!/usr/bin/env python3
"""Emit AST-only native BV source dependency census as JSON."""
import argparse
import json
from pathlib import Path
from spk_bv_research.dependency_census_v0k import census


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path.cwd())
    a=p.parse_args(argv)
    print(json.dumps(census(a.root),sort_keys=True,indent=2))


if __name__=='__main__':
    main()
