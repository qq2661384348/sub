# sub

This repository syncs the `v2ray免费节点分享` section from the upstream `free-nodes/v2rayfree` README into the root `sub.txt` file.

## What it does

- Fetches the upstream README as raw Markdown via GitHub's contents API
- Extracts the node list under `v2ray免费节点分享`
- Writes the extracted node URIs to `sub.txt`
- Commits and pushes only when `sub.txt` changes

## GitHub Actions

The workflow file is [`.github/workflows/sync-sub.yml`](.github/workflows/sync-sub.yml).

- Manual trigger: `workflow_dispatch`
- Scheduled trigger: UTC `00:00` and `12:00`
- Cron expression: `0 0,12 * * *`

## China-friendly mirror

- `sub.txt` mirror: `https://ghfile.geekertao.top/https://github.com/qq2661384348/sub/blob/master/sub.txt`

## Local run

```bash
python scripts/update_sub.py
```

The script fails without touching `sub.txt` if the upstream heading cannot be found or no valid node URIs can be extracted.
