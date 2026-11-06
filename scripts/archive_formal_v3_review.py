#!/usr/bin/env python3
"""Archive and verify obsolete review assets before removing their active copies."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('data/review','data/candidates/formal_v3_api_revision',
 'data/candidates/formal_v3_text_revision','data/candidates/formal_v3_text_revision_v2',
 'outputs/formal_v3_review_checks','outputs/formal_v3_cn_translation',
 'outputs/formal_v3_api_revision','outputs/formal_v3_api_candidates',
 'outputs/formal_v3_text_revision','outputs/formal_v3_text_revision_v2')
FILES = ('scripts/prepare_formal_v3_seed_review.py','scripts/prepare_formal_v3_review_results.py',
 'scripts/prepare_formal_v3_readable_original.py','scripts/translate_formal_v3_readable_cn.py',
 'scripts/check_formal_v3_reviews.py','src/longvision_eval/seed_review.py','tests/test_seed_review.py',
 'scripts/run_formal_v3_api_repair.py','src/longvision_eval/api_authoring.py','tests/test_api_authoring.py',
 'scripts/run_formal_v3_revision_pipeline.py','scripts/assemble_formal_v3_revision.py',
 'scripts/recover_formal_v3_source_response.py','scripts/mark_formal_v3_old_batch_superseded.py',
 'scripts/run_formal_v3_api_candidates.py','scripts/collect_formal_v3_api_candidates.py',
 'scripts/run_formal_v3_text_revision.py','tests/test_text_revision.py',
 'src/longvision_eval/candidate_validation.py','tests/test_candidate_validation.py',
 'documentation/reports/formal_v3_review_round1_20261105.md',
 'documentation/guides/FORMAL_V3_API_AUTHORING.md','documentation/guides/FORMAL_V3_API_CANDIDATES.md',
 'documentation/guides/FORMAL_V3_TEXT_REVISION.md')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    paths=[]
    for name in FILES:
        path=ROOT/name
        if path.is_file():
            paths.append(path)
        if path.suffix=='.py':
            cache=path.parent/'__pycache__'
            if cache.is_dir():
                paths.extend(p for p in cache.glob(path.stem+'.*.pyc') if p.is_file())
    for name in DIRECTORIES:
        directory=ROOT/name
        if directory.exists():
            paths.extend(p for p in directory.rglob('*') if p.is_file())
    for path in paths:
        if path.is_symlink() or path.resolve()!=path.absolute():
            raise ValueError('Refusing redirected archive target')
    paths=sorted(set(p.resolve() for p in paths))
    for path in paths:
        path.relative_to(ROOT)
        if path==ROOT or '.cache' in path.relative_to(ROOT).parts:
            raise ValueError('Unsafe archive target')
    destination=ROOT/'archives/formal_v3_review_workflow_20261106.zip'
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,
               'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    print(json.dumps({'execute':args.execute,'files':len(paths),'bytes':sum(x['bytes'] for x in manifest),
                      'archive':str(destination)},indent=2))
    if not args.execute:
        return
    completion=ROOT/'documentation/reports/formal_v3_extensions_status.json'
    if not completion.is_file() or json.loads(completion.read_text(encoding='utf-8')).get('trajectory_count')!=4224:
        raise ValueError('Build and validate the extended dataset before clearing review assets')
    if destination.exists():
        raise ValueError('Archive already exists; inspect before repeating cleanup')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path,item in zip(paths,manifest):
            archive.write(path,item['path'])
        archive.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC verification failed; nothing removed')
        for item in manifest:
            if hashlib.sha256(archive.read(item['path'])).hexdigest()!=item['sha256']:
                raise ValueError('Archive content verification failed; nothing removed')
    for path,item in zip(paths,manifest):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('A review file changed during archiving; stopped cleanup')
    for path,item in zip(paths,manifest):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('A file changed before removal; stopped cleanup')
        path.unlink()
    for name in DIRECTORIES:
        directory=ROOT/name
        if directory.exists():
            for sub in sorted((p for p in directory.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
                if not any(sub.iterdir()):
                    sub.rmdir()
            if not any(directory.iterdir()):
                directory.rmdir()
    report={'status':'archived_verified_then_removed','removed_file_count':len(paths),
            'archive':str(destination.relative_to(ROOT)),
            'archive_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'recoverable':True,'original_core_and_datasets_removed':False}
    (ROOT/'documentation/reports/formal_v3_review_archive.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
