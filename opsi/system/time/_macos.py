import os
import subprocess
from datetime import datetime


def set_system_datetime(utc_datetime: datetime) -> None:
	try:
		subprocess.run(
			["date", "-f", "%Y-%m-%d %H:%M:%S %Z", "-u", utc_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")], capture_output=True, check=True
		)
	except subprocess.CalledProcessError as err:
		raise RuntimeError(
			f"Failed to set system time as uid {os.geteuid()}: {err.returncode} - {err.stderr.decode(errors='replace')}"
		) from err
