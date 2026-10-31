"""Write or independently verify a canonical BV v0c evidence witness."""
import argparse
from pathlib import Path
from spk_backvalidation_v0.contract_v0 import canonical
from spk_backvalidation_v0.simulator_feedback_v0c import seal_v0c, verify_v0c


def main():
    p = argparse.ArgumentParser()
    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument('--write', type=Path)
    m.add_argument('--verify', type=Path)
    args = p.parse_args()
    if args.write is not None:
        args.write.write_text(seal_v0c() + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'file': args.write.name}))
    else:
        print(canonical(verify_v0c(args.verify.read_text(encoding='utf-8').rstrip('\n'))))


if __name__ == '__main__':
    main()
