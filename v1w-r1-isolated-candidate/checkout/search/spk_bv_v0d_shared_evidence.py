"""Write/independently replay real A3d forward-grant / BV shared-overlay pilot."""
import argparse
from pathlib import Path

from spk_backvalidation_v0.a3d_shared_grants_v0d import seal_v0d,verify_v0d
from spk_backvalidation_v0.contract_v0 import canonical


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write')
    group.add_argument('--verify')
    a=parser.parse_args()
    if a.write:
        Path(a.write).write_text(seal_v0d(),encoding='utf-8')
        print(canonical({'status':'WRITTEN','file':Path(a.write).name}))
    else:
        print(canonical(verify_v0d(Path(a.verify).read_text(encoding='utf-8'))))

if __name__=='__main__': main()
