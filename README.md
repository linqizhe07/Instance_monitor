# Lambda Cloud GPU Instance Monitor

A lightweight command-line tool that continuously monitors [Lambda Cloud](https://lambdalabs.com/service/gpu-cloud) for GPU instance availability and sends real-time notifications when instances become available.

Lambda's GPU instances (A100, H100, etc.) are often sold out. This script polls the Lambda API at a configurable interval and alerts you the moment a spot opens up — so you can grab it before it's gone.

## Features

- Polls the Lambda Cloud API for all GPU instance types on a configurable interval (default: 60s)
- Detects newly available instances and highlights them in the terminal
- Sends native OS notifications (macOS, Linux, Windows) with a terminal bell when new instances appear
- Notification cooldown prevents spam for the same instance type (default: 5 min)
- Displays pricing, GPU count, RAM, storage, and available regions for each instance
- Color-coded terminal output for easy scanning
- Validates your API key on startup

## Requirements

- Python 3.7+
- `requests` library

```bash
pip install requests
```

## Quick Start

1. Get an API key from [Lambda Cloud → API Keys](https://cloud.lambdalabs.com/api-keys).

2. Run the script:

   ```bash
   python3 lambda_monitor.py
   ```

3. Enter your API key when prompted (or set it as an environment variable):

   ```bash
   export LAMBDA_API_KEY="your-api-key-here"
   python3 lambda_monitor.py
   ```

4. Press `Ctrl+C` to stop.

## Configuration

Edit the constants near the top of `lambda_monitor.py`:

| Variable | Default | Description |
|---|---|---|
| `CHECK_INTERVAL` | `60` | Seconds between each API poll |
| `NOTIFY_COOLDOWN` | `300` | Seconds before re-notifying for the same instance type |

## Example Output

```
╔══════════════════════════════════════════════════╗
║       Lambda Cloud GPU Instance Monitor          ║
╚══════════════════════════════════════════════════╝

[14:32:10] 🟢 #5 Found 2 available instance types!
  🆕 NEW! 1x NVIDIA A100 (40 GB SXM4)
          💰 $1.10/hr  |  🖥 1 GPU  |  💾 200 GB RAM  |  📦 512 GB Storage
          🌍 Regions: us-tx-3
         1x NVIDIA H100 (80 GB SXM5)
          💰 $2.49/hr  |  🖥 1 GPU  |  💾 200 GB RAM  |  📦 512 GB Storage
          🌍 Regions: us-west-1
```

## System Notifications

The script sends native desktop notifications via:

- **macOS** — `osascript` (with Glass sound)
- **Linux** — `notify-send`
- **Windows** — PowerShell toast notifications

If the notification subsystem is unavailable, the script falls back silently to terminal bell only.

## License

MIT
