"""Take over an existing Qwen child, then audit and pause without starting another model."""
import argparse
import collections
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from longvision_eval.runner import write_json_atomic
from longvision_eval.run_metrics import summarize_runs
from run_formal_v3_18turn_queue import quality

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/formal_v3_18turn_runs'


def now():
    return datetime.now(timezone.utc).isoformat()


def inspect_process(pid):
    command = ('Get-CimInstance Win32_Process -Filter "ProcessId = ' + str(pid)
               + '" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def audit(directory):
    paths = list(directory.glob('V318-*.json'))
    rows, hashes = [], collections.defaultdict(list)
    for path in paths:
        item = json.loads(path.read_text(encoding='utf-8'))
        response = item['turns'][-1]['response']
        text = response.get('text', '')
        hashes[hashlib.sha256(text.strip().encode()).hexdigest()].append(item['sample_id'])
        rows.append({'sample_id': item['sample_id'], 'condition_id': item['condition_id'],
                     'split': item['split'], 'truncated': bool(response.get('truncated')),
                     'empty': not text.strip(), 'short_under_20_words': len(text.split()) < 20,
                     'output_tokens': response.get('output_tokens')})
    metrics = summarize_runs([directory])
    metrics['technical_quality_flags'] = quality(directory)
    write_json_atomic(directory / 'technical_metrics.json', metrics)
    config = json.loads((ROOT / 'configs/runs/formal_v3_18turn/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024.json').read_text(encoding='utf-8'))
    dataset = Path(config['dataset_path']) if 'dataset_path' in config else None
    # The run configuration's dataset field is version dependent; resolve explicitly.
    if dataset is None:
        dataset = Path('data/processed/formal_v3_18turn.jsonl')
    expected = {json.loads(line)['sample_id'] for line in (ROOT / dataset).open(encoding='utf-8') if line.strip()}
    actual = {row['sample_id'] for row in rows}
    report = {'created_at_utc': now(), 'run_id': directory.name, 'metrics': metrics,
              'expected_count': len(expected), 'missing_sample_ids': sorted(expected - actual),
              'unexpected_sample_ids': sorted(actual - expected),
              'truncated_sample_ids': [r['sample_id'] for r in rows if r['truncated']],
              'short_answer_sample_ids': [r['sample_id'] for r in rows if r['short_under_20_words']],
              'exact_duplicate_response_groups': [v for v in hashes.values() if len(v) > 1],
              'sample_checks': rows,
              'interpretation': 'Technical checks only. Short or duplicate answers are review flags, not safety labels. No ASR or safety-rate conclusion.'}
    write_json_atomic(directory / 'completion_audit.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-pid', type=int, required=True)
    parser.add_argument('--child-pid', type=int, required=True)
    args = parser.parse_args()
    state_path = OUT / 'queue_status.json'
    state = json.loads(state_path.read_text(encoding='utf-8'))
    if state.get('model') != 'qwen25vl7b' or state.get('phase') != 'formal':
        raise RuntimeError('Expected the current Qwen formal stage; no processes changed.')
    parent = inspect_process(args.controller_pid)
    child = inspect_process(args.child_pid)
    if not parent or 'scripts/run_formal_v3_18turn_queue.py' not in parent['CommandLine']:
        raise RuntimeError('Controller identity mismatch; no processes changed.')
    if not child or 'formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024.json --resume' not in child['CommandLine']:
        raise RuntimeError('Qwen child identity mismatch; no processes changed.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000 | 0x1000, False, args.child_pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    # Deliberately omit /T: leave the active model child running uninterrupted.
    subprocess.run(['taskkill.exe', '/PID', str(args.controller_pid), '/F'], check=True)
    lock = OUT / 'serial_queue.lock'
    lock.write_text(str(os.getpid()), encoding='ascii')
    state.update(pid=os.getpid(), controller='pause_after_qwen_and_audit',
                 previous_controller_pid=args.controller_pid, pause_after_model='qwen25vl7b',
                 pending_models_paused=True, pause_requested_at_utc=now())
    directory = ROOT / state['run_dir']
    try:
        while True:
            state.update(results_written=len(list(directory.glob('V318-*.json'))),
                         error_files=len(list((directory / 'errors').glob('*.json'))),
                         updated_at_utc=now())
            write_json_atomic(state_path, state)
            wait = kernel.WaitForSingleObject(handle, 10000)
            if wait == 0:
                break
            if wait != 258:
                raise ctypes.WinError(ctypes.get_last_error())
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        report = audit(directory)
        complete = (code.value == 0 and not report['missing_sample_ids']
                    and not report['unexpected_sample_ids'] and not report['metrics']['error_file_count'])
        state.update(status='paused_after_qwen' if complete else 'stopped_needs_attention',
                     phase='completion_audit_finished', child_pid=None, child_exit_code=code.value,
                     results_written=report['metrics']['sample_count'],
                     last_technical_metrics=report['metrics'], updated_at_utc=now(),
                     completion_audit=str((directory / 'completion_audit.json').relative_to(ROOT)))
        if complete:
            state['completed_models'] = ['qwen25vl7b']
        write_json_atomic(state_path, state)
        handoff = ROOT / 'documentation/PROJECT_HANDOFF.md'
        content = handoff.read_text(encoding='utf-8')
        marker = '<!-- QWEN_PAUSE_AUDIT_RESULT -->'
        note = ('\n' + marker + '\nQwen暂停收尾检查（' + now() + '）：状态`'
                + state['status'] + '`，正式结果' + str(state['results_written'])
                + '/4864；错误' + str(report['metrics']['error_file_count'])
                + '，截断' + str(len(report['truncated_sample_ids']))
                + '。其他三模型保持暂停，未经用户重新授权不得恢复。完整技术检查见`'
                + state['completion_audit'] + '`；尚无人工安全标注，不报告ASR/安全率。\n')
        if marker not in content:
            handoff.write_text(content + note, encoding='utf-8')
    except Exception as error:
        state.update(status='audit_monitor_needs_attention', detail=str(error), updated_at_utc=now())
        write_json_atomic(state_path, state)
        raise
    finally:
        kernel.CloseHandle(handle)
        if lock.exists() and lock.read_text().strip() == str(os.getpid()):
            lock.unlink()


if __name__ == '__main__':
    main()
