import os
import json
from datetime import datetime

def get_latest_change(results_dir="results"):
    """
    Returns the latest change (most recent detected_at) from all job results files.
    """
    latest = None
    latest_file = None
    latest_job_id = None
    latest_time = None
    for fname in os.listdir(results_dir):
        if not fname.endswith('.json'):
            continue
        job_id = fname.replace('.json', '')
        fpath = os.path.join(results_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                changes = json.load(f)
                if not changes:
                    continue
                # Find the most recent change in this file
                for change in changes[::-1]:  # reverse for efficiency
                    detected_at = change.get('detected_at')
                    if detected_at:
                        dt = datetime.fromisoformat(detected_at)
                        if latest_time is None or dt > latest_time:
                            latest = change
                            latest_file = fname
                            latest_job_id = job_id
                            latest_time = dt
                        break  # Only need the latest per file
        except Exception as e:
            continue
    if latest:
        return {
            'job_id': latest_job_id,
            'results_file': latest_file,
            'change': latest,
            'detected_at': latest.get('detected_at')
        }
    return None

def get_latest_changes_per_job(results_dir="results"):
    """
    Returns the latest change for each job as a list.
    """
    latest_changes = []
    for fname in os.listdir(results_dir):
        if not fname.endswith('.json'):
            continue
        job_id = fname.replace('.json', '')
        fpath = os.path.join(results_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                changes = json.load(f)
                if not changes:
                    continue
                latest = changes[-1]
                latest_changes.append({
                    'job_id': job_id,
                    'results_file': fname,
                    'change': latest,
                    'detected_at': latest.get('detected_at')
                })
        except Exception as e:
            continue
    # Sort by detected_at descending
    latest_changes.sort(key=lambda x: x.get('detected_at') or '', reverse=True)
    return latest_changes
