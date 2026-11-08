"""Resume only the frozen local Qwen formal run, audit, then stop without other models."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from longvision_eval.provenance import run_provenance
from longvision_eval.runner import write_json_atomic
from pause_after_qwen_and_audit import audit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/formal_v3_18turn_runs'
CONFIG = 'configs/runs/formal_v3_18turn/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now():
    return datetime.now(timezone.utc).isoformat()


def check_saved():
    config = load(ROOT / CONFIG)
    model = load(ROOT / config['model_config'])
    directory = ROOT / config['output_dir'] / config['run_id']
    provenance = run_provenance(config, model, ROOT)
    manifest = load(directory / 'run_manifest.json')
    if provenance != manifest['provenance']:
        raise ValueError('Frozen run provenance differs; do not mix results')
    if manifest['model_configuration'] != model:
        raise ValueError('Frozen model configuration differs')
    receipt = load(directory / 'pause_receipt.json')
    for name, expected in receipt['result_sha256'].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError('A previously saved answer changed: ' + name)
    return config, directory, len(list(directory.glob('V318-*.json')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    config, directory, count = check_saved()
    print(json.dumps({'verified_saved_results': count, 'target': 4864,
                      'run_id': config['run_id'], 'other_models_will_start': False}), flush=True)
    if args.check_only:
        return
    lock = OUT / 'serial_queue.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(descriptor, str(os.getpid()).encode())
    os.close(descriptor)
    state_path = OUT / 'queue_status.json'
    state = load(state_path)
    state.update(status='running', phase='formal', pid=os.getpid(), child_pid=None,
                 controller='resume_local_qwen', model='qwen25vl7b', resumed_at_utc=now(),
                 resume_requires_user_instruction=False, results_written=count,
                 pending_models_paused=True, pause_after_model='qwen25vl7b')
    def status(**changes):
        state.update(changes, updated_at_utc=now())
        write_json_atomic(state_path, state)
    process = None
    try:
        env = os.environ.copy()
        env.update(HF_HOME=str(ROOT / '.cache/huggingface'), HF_HUB_OFFLINE='1',
                   TRANSFORMERS_OFFLINE='1', PYTHONPATH=str(ROOT / 'src'),
                   PYTHONUTF8='1', PYTHONUNBUFFERED='1')
        path = OUT / 'logs/qwen25vl7b-formal.log'
        with path.open('a', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, 'scripts/run_experiment.py', '--config', CONFIG, '--resume'],
                                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            status(child_pid=process.pid, log=path.relative_to(ROOT).as_posix())
            while process.poll() is None:
                status(results_written=len(list(directory.glob('V318-*.json'))),
                       error_files=len(list((directory / 'errors').glob('*.json'))))
                time.sleep(10)
        report = audit(directory)
        complete = (process.returncode == 0 and not report['missing_sample_ids']
                    and not report['unexpected_sample_ids'] and not report['metrics']['error_file_count'])
        report.update(complete=complete, status='paused_after_qwen' if complete else 'stopped_needs_attention')
        write_json_atomic(directory / 'completion_audit.json', report)
        status(status=report['status'], phase='completion_audit_finished', pid=None, child_pid=None,
               child_exit_code=process.returncode, results_written=report['metrics']['sample_count'],
               error_files=report['metrics']['error_file_count'], last_technical_metrics=report['metrics'],
               resume_requires_user_instruction=True, completed_models=['qwen25vl7b'] if complete else [],
               completion_audit=(directory / 'completion_audit.json').relative_to(ROOT).as_posix())
        note = ('\n\nQwen单模型恢复运行收尾（' + now() + '）：`' + report['status'] + '`，'
                + str(state['results_written']) + '/4864，错误' + str(state['error_files'])
                + '，截断' + str(len(report['truncated_sample_ids']))
                + '；已停止，不启动其他模型。技术审计见`' + state['completion_audit']
                + '`；未进行安全标签评价，不报告ASR/安全率。\n')
        with (ROOT / 'documentation/PROJECT_HANDOFF.md').open('a', encoding='utf-8') as f:
            f.write(note)
    except BaseException as error:
        status(status='resume_monitor_needs_attention', detail=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        # Leave the lock intact if a child survived an interrupted monitor.
        if (process is None or process.poll() is not None) and lock.exists() and lock.read_text().strip() == str(os.getpid()):
            lock.unlink()


if __name__ == '__main__':
    main()
