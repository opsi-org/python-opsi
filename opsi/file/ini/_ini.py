# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import builtins
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from configupdater import ConfigUpdater

from opsi.logging import get_logger

ENCODING = "utf-8"

tmp = Path("/tmp") / "test.ini"


logger = get_logger("opsi")


class IniParseError(Exception):
	"""Raised when an INI file cannot be read or parsed."""

	pass


# INIFile class, should be used via opsi.file.ini.open
class INIFile:
	"""
	Represents an INI configuration file and provides methods to read
	and modify its contents.
	"""

	def __init__(self, filename: str | os.PathLike[str], /, *, encoding: str = ENCODING) -> None:
		"""
		Initialize the INIFile instance.
		:param filename: Path to the INI file.
		:param encoding: Encoding to use when reading the file.
		"""
		self.filename = Path(filename)
		self.encoding = encoding

		# Create the INI file if it does not exist
		if not self.filename.exists():
			logger.info("INI file does not exist, creating it: %s", self.filename)
			self.filename.touch()

		self._updater = ConfigUpdater()
		try:
			logger.debug("Reading INI file '%s' with encoding '%s'", self.filename, encoding)
			self._updater.read(self.filename, encoding=encoding)
		except Exception as e:
			logger.error("Failed to read INI file '%s'", self.filename)
			raise IniParseError(f"Failed to read INI file {self.filename}") from e

	def set_option(self, section: str, option: str, value: str, /, *, overwrite: bool = True, create: bool = True) -> None:
		"""
		Add or update an option in a specific section.

		:param section: Section name
		:param option: Option name
		:param value: Value to set
		:param overwrite: Whether to overwrite existing values
		:param create: Whether to create the section and option if it does not exist
		"""
		if not self._updater.has_section(section):
			if create:
				logger.info("Creating section '%s'", section)
				self._updater.add_section(section)
			else:
				# We want don't want to create the section if create is False
				logger.debug("Section '%s' does not exist and create=False, skipping set_option", section)
				return

		if not overwrite and option in self._updater[section]:
			# We don't want to overwrite existing values if overwrite is False
			logger.debug("Option '%s' in section '%s' exists and overwrite=False, skipping", option, section)
			return

		if not create and option not in self._updater[section]:
			# We don't want to create the option if create is False and the option does not exist
			logger.debug("Option '%s' does not exist in section '%s' and create=False, skipping", option, section)
			return

		logger.info("Setting option '%s' in section '%s'", option, section)
		self._updater[section][option] = value

	def has_section(self, section: str, /) -> bool:
		"""
		Check if a section exists in the INI file.

		:param section: Section name
		:return: True if the section exists, False otherwise
		"""
		return self._updater.has_section(section)

	def has_option(self, section: str, option: str, /) -> bool:
		"""
		Check if an option exists in a specific section.

		:param section: Section name
		:param option: Option name
		:return: True if the option exists in the section, False otherwise
		"""
		# Use this method which is case insensitive.
		# Using self._updater.has_section(section) and option in self._updater[section] does weird stuff
		# and would require to call option.lower(). Making this method case sensitive is more complicated.
		return self._updater.has_option(section, option)

	def merge(self, other: INIFile) -> None:
		"""
		Merge another INIFile into this one, overwriting existing options.

		:param other: Another INIFile instance.
		:type other: INIFile
		"""
		for section in other._updater.sections():
			if not self._updater.has_section(section):
				self._updater.add_section(section)
			for name, option in other._updater[section].items():
				self._updater[section][name] = option.value

	__or__ = merge

	def get_option(self, section: str, option: str, /, *, default: str = "") -> str:
		"""
		Get the value of a specific option.

		:param section: Section name
		:param option: Option name
		:param default: Default value if option is not found
		:return: Value of the option or default if not found"""
		if self.has_option(section, option):
			return self._updater[section][option].value or default
		return default

	def remove_section(self, section: str, /) -> bool:
		"""
		Remove a section from the INI file.
		:param section: Section name to remove
		:return: True if the section was removed, False if it did not exist
		"""
		if self._updater.has_section(section):
			logger.info("Removing section '%s'", section)
			return self._updater.remove_section(section)
		return False

	def remove_option(self, section: str, option: str, /) -> bool:
		"""
		Remove an option from a specific section.
		:param section: Section name
		:param option: Option name to remove
		:return: True if the option was removed, False if it did not exist
		"""
		if self.has_option(section, option):
			logger.info("Removing option '%s' from section '%s'", option, section)
			return self._updater.remove_option(section, option)

		logger.debug("Option '%s' in section '%s' does not exist, cannot remove", option, section)
		return False

	def list_sections(self, /) -> list[str]:
		"""
		Get all section names from the INI file.
		:return: List of section names
		"""
		return self._updater.sections()

	def replace_option(self, old_option: str, old_value: str, new_option: str, new_value: str, /) -> None:
		"""
		Replace an option with a new option and value in all sections
		if the old option has the specified old value.

		:param old_option: The option name to be replaced
		:param old_value: The value that the old option must have to be replaced
		:param new_option: The new option name to set
		:param new_value: The new value to set for the new option
		"""
		for section in self._updater.sections():
			if old_option in self._updater[section] and self._updater[section][old_option].value == old_value:
				logger.info("Replacing option '%s' with '%s' in section '%s'", old_option, new_option, section)
				self._updater[section][new_option] = new_value
				self._updater.remove_option(section, old_option)

	def _update_file(self) -> None:
		"""Write changes back to the INI file."""
		with builtins.open(self.filename, "w", encoding=self.encoding) as f:
			self._updater.write(f)


@contextmanager
def open(ini_file: str | os.PathLike[str], /, *, encoding: str = ENCODING) -> Generator[INIFile, None, None]:
	"""
	Open an INI file for reading and modification.

	Changes made to the INIFile are automatically written back to disk
	when leaving the context manager.

	:param ini_file: Path to the INI file.
	:param encoding: Encoding of the INI file.
	:return: INIFile instance for the opened INI file.

	Example:
	Basic usage with a context manager::

	with ini.open("config.ini") as ini_file:
	version = ini_file.get_option("General", "version")
	ini_file.set_option("General", "version", "5.0")
	"""

	logger.debug("Opening INI file '%s'", ini_file)
	_ini_file = INIFile(ini_file, encoding=encoding)

	yield _ini_file
	logger.debug("Closing INI file '%s'", ini_file)
	_ini_file._update_file()


def set_option(
	ini_file: str | os.PathLike[str],
	section: str,
	option: str,
	value: str,
	/,
	*,
	overwrite: bool = True,
	create: bool = True,
	encoding: str = ENCODING,
) -> None:
	"""
	Update a specific value in an INI configuration file.

	This is a convenience function for INIFile.set_option."""
	with open(ini_file, encoding=encoding) as config:
		config.set_option(section, option, value, overwrite=overwrite, create=create)


def has_section(ini_file: str | os.PathLike[str], section: str, /, *, encoding: str = ENCODING) -> bool:
	"""
	Check if a section exists in an INI configuration file.

	This is a convenience function for INIFile.has_section."""
	with open(ini_file, encoding=encoding) as config:
		return config.has_section(section)


def has_option(ini_file: str | os.PathLike[str], section: str, option: str, /, *, encoding: str = ENCODING) -> bool:
	"""
	Check if an option exists in a specific section of an INI configuration file.

	This is a convenience function for INIFile.has_option."""
	with open(ini_file, encoding=encoding) as config:
		return config.has_option(section, option)


def get_option(ini_file: str | os.PathLike[str], section: str, option: str, /, *, default: str = "", encoding: str = ENCODING) -> str:
	"""
	Reads a specific value from an INI configuration file.

	This is a convenience function for INIFile.get_option."""
	with open(ini_file, encoding=encoding) as config:
		return config.get_option(section, option, default=default)


def list_sections(ini_file: str | os.PathLike[str], /, *, encoding: str = ENCODING) -> list[str]:
	"""
	Get all sections from an INI configuration file.

	This is a convenience function for INIFile.get_section_names."""
	with open(ini_file, encoding=encoding) as config:
		return config.list_sections()


def replace_option(
	ini_file: str | os.PathLike[str], old_option: str, old_value: str, new_option: str, new_value: str, /, *, encoding: str = ENCODING
) -> None:
	"""
	Replace an option with a new option and value in all sections of an INI configuration file
	if the old option has the specified old value.

	This is a convenience function for INIFile.replace_option."""
	with open(ini_file, encoding=encoding) as config:
		config.replace_option(old_option, old_value, new_option, new_value)


def remove_section(ini_file: str | os.PathLike[str], section: str, /, *, encoding: str = ENCODING) -> bool:
	"""
	Remove a section from an INI configuration file.

	This is a convenience function for INIFile.remove_section."""
	with open(ini_file, encoding=encoding) as config:
		return config.remove_section(section)


def remove_option(ini_file: str | os.PathLike[str], section: str, option: str, /, *, encoding: str = ENCODING) -> bool:
	"""
	Remove an option from a section in an INI configuration file.

	This is a convenience function for INIFile.remove_option."""
	with open(ini_file, encoding=encoding) as config:
		return config.remove_option(section, option)
