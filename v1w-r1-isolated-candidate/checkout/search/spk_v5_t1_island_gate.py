"""Create-only V5 T1/T2 source-backed diagnostic report."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spk_v5_research.island_objective_v5t1 import run_pilot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dest = args.output.absolute()
    if dest.is_relative_to(root) or dest.is_symlink() or dest.exists() or dest.parent.is_symlink():
        parser.error('unsafe or existing create-only report path')
    result = run_pilot()
    payload = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()
    with dest.open('xb') as handle:
        handle.write(payload)
    print(json.dumps({k: result[k] for k in ('status','train_episode_count','evaluation_episode_count',
       'pilot_local_feedback_loss','pilot_placebo_loss','frozen_baseline_loss',
       'supervised_oracle_upper_bound_loss_NOT_LEARNED','false_positive_local_ACKs_train')}, sort_keys=True))


if __name__ == '__main__':
    main()
