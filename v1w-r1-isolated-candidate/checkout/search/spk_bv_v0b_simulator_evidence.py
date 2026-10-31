"""Generate/verify simulator-backed BV v0b evidence, independently rerunning frozen engines."""
import argparse
from pathlib import Path
from spk_backvalidation_v0.contract_v0 import canonical, digest
from spk_backvalidation_v0.simulator_evidence_v0b import seal_v0b, verify_v0b


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--verify', type=Path)
    arg = ap.parse_args()
    if arg.write:
        arg.write.write_text(seal_v0b() + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'file': arg.write.name}))
    else:
        text = arg.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v0b(text)))


if __name__ == '__main__':
    main()
