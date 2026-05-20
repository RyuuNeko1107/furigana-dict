"""GitHub deployments の古い entry を整理 (= 最新 N 件残して 残全部削除)。

GitHub Settings → Environments → github-pages → Deployments の履歴肥大化対策。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def gh_api(method: str, path: str, body: str | None = None) -> str:
    args = ["gh", "api", "-X", method, path]
    if body is not None:
        args += ["--input", "-"]
        return subprocess.run(args, input=body, capture_output=True, text=True, check=False).stdout
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def list_deployment_ids(repo: str) -> list[int]:
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/deployments", "--paginate", "-q", ".[].id"],
        capture_output=True, text=True, check=False,
    ).stdout
    return [int(x) for x in out.split() if x.strip().isdigit()]


def set_inactive(repo: str, deployment_id: int) -> None:
    body = json.dumps({"state": "inactive"})
    subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{repo}/deployments/{deployment_id}/statuses",
         "-f", "state=inactive"],
        capture_output=True, text=True, check=False,
    )


def delete_deployment(repo: str, deployment_id: int) -> bool:
    result = subprocess.run(
        ["gh", "api", "-X", "DELETE", f"repos/{repo}/deployments/{deployment_id}"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="RyuuNeko1107/ja-furigana-dict")
    ap.add_argument("--keep", type=int, default=10, help="最新 N 件残す")
    args = ap.parse_args()

    ids = list_deployment_ids(args.repo)
    print(f"[info] {len(ids)} deployments found")
    to_delete = ids[args.keep:]
    print(f"[info] keeping newest {args.keep}, deleting {len(to_delete)}")

    deleted = 0
    for i, did in enumerate(to_delete, 1):
        # まず inactive に set
        set_inactive(args.repo, did)
        # 削除
        if delete_deployment(args.repo, did):
            deleted += 1
        if i % 20 == 0:
            print(f"[info] {i}/{len(to_delete)} processed ({deleted} deleted)", file=sys.stderr)

    print(f"[done] deleted {deleted}/{len(to_delete)}")


if __name__ == "__main__":
    main()
