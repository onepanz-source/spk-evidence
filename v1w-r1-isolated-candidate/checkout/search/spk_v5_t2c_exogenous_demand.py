"""SPK V5-T2c deterministic create-only observation; synthetic and nonblind."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spk_v5_research.island_endogenous_demand_v5t2c import run_t2c


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    dest=args.output.absolute()
    if (dest.exists() or dest.is_symlink() or dest.is_relative_to(root)
            or not dest.parent.exists() or dest.parent.is_symlink()):
        parser.error('unsafe or existing create-only report path')
    content=(json.dumps(run_t2c(),sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    with dest.open('xb') as f:f.write(content)
    print('SPK V5-T2c report created:',dest)

if __name__ == '__main__':main()
