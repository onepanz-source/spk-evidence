"""Create-only V5-T2d canonical experiment; accepts no user-mutable policy claims."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from spk_v5_research.island_sensor_robustness_v5t2d import run_t2d


def main():
    p=argparse.ArgumentParser()
    p.add_argument('output',type=Path)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    dest=args.output.absolute()
    if (dest.exists() or dest.is_symlink() or dest.is_relative_to(root)
            or not dest.parent.is_dir() or dest.parent.is_symlink()):
        p.error('unsafe or existing create-only report path')
    content=(json.dumps(run_t2d(),sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    with dest.open('xb') as f:f.write(content)
    print('V5-T2d source-engine research report created:',dest)

if __name__=='__main__':main()
