from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows

if is_linux():
	from ._linux import install_ca, load_cas, load_ca, remove_ca
elif is_windows():
	from ._windows import install_ca, load_cas, load_ca, remove_ca
elif is_macos():
	from ._macos import install_ca, load_cas, load_ca, remove_ca
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = ["install_ca", "load_cas", "load_ca", "remove_ca"]
