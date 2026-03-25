# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest

from opsi.file.inf import (
	DeviceType,
	INFDriverVer,
	INFFile,
	INFHardwareID,
	INFManufacturer,
	INFTargetOSVersion,
	INFVersion,
)
from opsi.file.inf._inffile import _to_int, current_timestamp, reg_dword, reg_expand_sz, reg_hex, reg_multi_sz
from opsi.opsi.service.model.type import Architecture

DATA_PATH = Path("tests") / "data" / "inffile"


def test_to_int() -> None:
	assert _to_int("0") == 0
	assert _to_int("1") == 1
	assert _to_int("10") == 10
	assert _to_int("10", 0) == 10
	assert _to_int("10", 16) == 16
	assert _to_int("0x00000001") == 1
	assert _to_int("0x00010000") == 65536
	assert _to_int("CC", 16) == 204
	assert _to_int("AA") == 170


def test_reg_dword() -> None:
	assert reg_dword(1) == "dword:00000001"
	assert reg_dword(0x12345678) == "dword:12345678"


def test_reg_hex() -> None:
	assert reg_hex("test") == "74,00,65,00,73,00,74,00,00,00"
	assert reg_hex("test", null_terminated=True) == "74,00,65,00,73,00,74,00,00,00"
	assert reg_hex("test", null_terminated=False) == "74,00,65,00,73,00,74,00"
	assert reg_hex(b"test") == "74,65,73,74,00,00"
	assert reg_hex(b"test", null_terminated=False) == "74,65,73,74"
	assert reg_hex("ÄÖÜ") == "c4,00,d6,00,dc,00,00,00"


def test_reg_multi_sz() -> None:
	assert reg_multi_sz(["arcsas_Inst.NT", "arcsas_MSIX.NT"]) == (
		"hex(7):61,00,72,00,63,00,73,00,61,00,73,00,5f,00"
		",49,00,6e,00,73,00,74,00,2e,00,4e,00,54,00,00,00"
		",61,00,72,00,63,00,73,00,61,00,73,00,5f,00,4d,00"
		",53,00,49,00,58,00,2e,00,4e,00,54,00,00,00,00,00"
	)
	assert reg_multi_sz("ß") == "hex(7):df,00,00,00,00,00"
	assert reg_multi_sz([b"\x01", b"\x02"]) == "hex(7):01,00,00,02,00,00,00,00"
	assert reg_multi_sz("") == "hex(7):00,00,00,00"
	with pytest.raises(ValueError, match="No values given"):
		assert reg_multi_sz([])


def test_reg_expand_sz() -> None:
	assert reg_expand_sz("test") == "hex(2):74,00,65,00,73,00,74,00,00,00"


def test_current_timestamp() -> None:
	assert abs(current_timestamp() - datetime.now().timestamp()) < 1


def test_inf_target_os_version() -> None:
	assert INFTargetOSVersion.from_string("NTamd64.10.0...14393") == INFTargetOSVersion(
		Architecture=Architecture.X64, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=14393
	)
	assert INFTargetOSVersion.from_string("NTx86") == INFTargetOSVersion(Architecture=Architecture.X86)
	with pytest.raises(ValueError, match="nvalid TargetOSVersion"):
		INFTargetOSVersion.from_string("amd64.10.0.14393")

	assert not INFTargetOSVersion(Architecture=Architecture.X86).matches_platform(INFTargetOSVersion(Architecture=Architecture.X64))
	assert not INFTargetOSVersion(Architecture=Architecture.X86).matches_platform(
		INFTargetOSVersion(Architecture=Architecture.X86, ProductType=1)
	)

	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0)
		)
		== 0
	)
	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19044).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19044)
		)
		== 0
	)
	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19044).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=22621)
		)
		== -1
	)
	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19044).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0)
		)
		== 1
	)
	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19044)
		)
		== -1
	)
	assert (
		INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=6, OSMinorVersion=3, BuildNumber=9600).compare_version(
			INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=10, OSMinorVersion=0)
		)
		== -1
	)


def test_inf_hardware_id() -> None:
	hw_str = "PCI\\VEN_1AF4&DEV_1004&SUBSYS_00080007&REV_00"
	hw_id = INFHardwareID(
		device_type=DeviceType("PCI"),
		vendor_id="1AF4",
		device_id="1004",
		subsystem_vendor_id="0007",
		subsystem_device_id="0008",
		revision="00",
	)
	assert INFHardwareID.from_string(hw_str) == hw_id
	assert hw_id.to_string() == hw_str


def test_fail_open() -> None:
	inf_file = "/not/found"
	with pytest.raises(FileNotFoundError):
		INFFile(path=inf_file)


def test_hash() -> None:
	filepath = DATA_PATH / "vioscsi_amd64.inf"
	inf_file = INFFile(path=filepath)
	assert hex(inf_file.hash) == "0x580a262bfd85344b"


@pytest.mark.parametrize(
	"filename, expected_version",
	(
		(
			"lsi_sas.inf",
			INFVersion(
				Class="SCSIAdapter",
				ClassGUID="4D36E97B-E325-11CE-BFC1-08002BE10318",
				Provider="LSI",
				DriverVer=INFDriverVer(date=datetime(2008, 7, 7, tzinfo=timezone.utc), version=(1, 28, 3, 52)),
			),
		),
		(
			"netkvm.inf",
			INFVersion(
				Class="Net",
				ClassGUID="4D36E972-E325-11CE-BFC1-08002BE10318",
				Provider="Red Hat, Inc.",
				DriverVer=INFDriverVer(date=datetime(2022, 8, 18, tzinfo=timezone.utc), version=(100, 91, 104, 22500)),
			),
		),
		(
			"ser2pl.inf",
			INFVersion(
				Class="Ports",
				ClassGUID="4D36E978-E325-11CE-BFC1-08002BE10318",
				Provider="Prolific",
				DriverVer=INFDriverVer(date=datetime(2002, 12, 31, tzinfo=timezone.utc), version=(2, 0, 0, 7)),
			),
		),
		(
			"vioscsi_amd64.inf",
			INFVersion(
				Class="SCSIAdapter",
				ClassGUID="4D36E97B-E325-11CE-BFC1-08002BE10318",
				Provider="Red Hat, Inc.",
				DriverVer=INFDriverVer(date=datetime(2021, 8, 30, tzinfo=timezone.utc), version=(100, 85, 104, 20800)),
			),
		),
		(
			"vioscsi_x86.inf",
			INFVersion(
				Class="SCSIAdapter",
				ClassGUID="4D36E97B-E325-11CE-BFC1-08002BE10318",
				Provider="Red Hat, Inc.",
				DriverVer=INFDriverVer(date=datetime(2021, 12, 2, tzinfo=timezone.utc), version=(100, 90, 104, 21500)),
			),
		),
		(
			"viostor.inf",
			INFVersion(
				Class="SCSIAdapter",
				ClassGUID="4D36E97B-E325-11CE-BFC1-08002BE10318",
				Provider="Red Hat, Inc.",
				DriverVer=INFDriverVer(date=datetime(2022, 8, 18, tzinfo=timezone.utc), version=(100, 91, 104, 22500)),
			),
		),
	),
)
def test_version(filename: str, expected_version: INFVersion) -> None:
	filepath = DATA_PATH / filename
	inf_file = INFFile(path=filepath)
	inf_file.parse()
	assert inf_file.version == expected_version


@pytest.mark.parametrize(
	"filename, expected_manufacturers",
	(
		(
			"lsi_sas.inf",
			[
				INFManufacturer(
					name="LSI",
					models_section_name="LSI",
					target_os_version=[
						INFTargetOSVersion(Architecture=Architecture.X86),
						INFTargetOSVersion(Architecture=Architecture.IA64),
						INFTargetOSVersion(Architecture=Architecture.X64),
					],
				),
				INFManufacturer(
					name="Dell",
					models_section_name="DELL",
					target_os_version=[
						INFTargetOSVersion(Architecture=Architecture.X86),
						INFTargetOSVersion(Architecture=Architecture.IA64),
						INFTargetOSVersion(Architecture=Architecture.X64),
					],
				),
			],
		),
		(
			"netkvm.inf",
			[
				INFManufacturer(
					name="Red Hat, Inc.",
					models_section_name="NetKVM",
					target_os_version=[INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=3)],
				)
			],
		),
		(
			"ser2pl.inf",
			[INFManufacturer(name="Prolific", models_section_name="Pro", target_os_version=[])],
		),
		(
			"vioscsi_amd64.inf",
			[
				INFManufacturer(
					name="Red Hat, Inc.",
					models_section_name="VirtioScsi",
					target_os_version=[INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=3)],
				)
			],
		),
		(
			"vioscsi_x86.inf",
			[
				INFManufacturer(
					name="Red Hat, Inc.",
					models_section_name="VirtioScsi",
					target_os_version=[INFTargetOSVersion(Architecture=Architecture.X86, OSMajorVersion=6, OSMinorVersion=3)],
				)
			],
		),
		(
			"viostor.inf",
			[
				INFManufacturer(
					name="Red Hat, Inc.",
					models_section_name="VioStor",
					target_os_version=[INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=3)],
				)
			],
		),
	),
)
def test_manufacturer(filename: str, expected_manufacturers: list[INFManufacturer]) -> None:
	filepath = DATA_PATH / filename
	inf_file = INFFile(path=filepath)
	inf_file.parse()
	assert inf_file._manufacturers == expected_manufacturers


def test_parse_encodings(tmp_path: Path) -> None:
	test_file = DATA_PATH / "vioscsi_amd64.inf"
	data = test_file.read_text("ascii") + "üöä"
	test_file = tmp_path / "test.inf"

	for encoding in ("utf-16", "windows-1258", "utf-8"):
		with open(test_file, mode="w", encoding=encoding) as file:
			file.write(data)
		inf_file = INFFile(path=test_file)
		inf_file.parse()
		assert inf_file._encoding == encoding

	with open(test_file, mode="w", encoding=encoding) as file:
		file.write("")

	inf_file = INFFile(path=test_file)
	with pytest.raises(RuntimeError):
		inf_file.parse()


def test_strings_vioscsi_amd64() -> None:
	test_file = DATA_PATH / "vioscsi_amd64.inf"
	inf_file = INFFile(path=test_file, inf_name="vioscsi.inf")
	inf_file.parse()
	assert inf_file._strings == {
		"REG_DWORD": "0x00010001",
		"REG_EXPAND_SZ": "0x00020000",
		"SERVICE_BOOT_START": "0",
		"SERVICE_ERROR_NORMAL": "1",
		"SERVICE_KERNEL_DRIVER": "1",
		"VENDOR": "Red Hat, Inc.",
		"VirtioScsi.DeviceDesc": "Red Hat VirtIO SCSI pass-through controller",
		"VirtioScsi.SVCDESC": "Red Hat VirtIO SCSI pass-through Service",
		"diskId1": "Red Hat VirtIO SCSI pass-through controller Installation Disk",
	}


def test_get_services_reg_vioscsi_amd64() -> None:
	test_file = DATA_PATH / "vioscsi_amd64.inf"
	inf_file = INFFile(path=test_file, inf_name="vioscsi.inf")
	reg = inf_file.get_services_reg(
		hardware_id=INFHardwareID(device_type=DeviceType.PCI, vendor_id="1AF4", device_id="1004"),
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
	)

	assert reg == dedent(
		r"""
		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\vioscsi]
		"ImagePath"=hex(2):73,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,00,5c,00,64,00,72,00,69,00,76,00,65,00,72,00,73,00,5c,00,76,00,69,00,6f,00,73,00,63,00,73,00,69,00,2e,00,73,00,79,00,73,00,00,00
		"DisplayName"="@oem0.inf,%VirtioScsi.SVCDESC%;Red Hat VirtIO SCSI pass-through Service"
		"Type"=dword:00000001
		"Start"=dword:00000000
		"ErrorControl"=dword:00000001
		"Owners"=hex(7):6f,00,65,00,6d,00,30,00,2e,00,69,00,6e,00,66,00,00,00,00,00
		"Group"="SCSI miniport"

		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\vioscsi\Parameters]
		"BusType"=dword:0000000a

		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\vioscsi\Parameters\PnpInterface]
		"5"=dword:00000001

		"""
	).lstrip().replace("\n", "\r\n")

	reg = inf_file.get_services_reg(
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1AF4",
			device_id="1004",
			subsystem_vendor_id="0008",
			subsystem_device_id="0007",
			revision="00",
		),
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		services_root=r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services",
	)

	assert reg == dedent(
		r"""
		[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\vioscsi]
		"ImagePath"=hex(2):73,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,00,5c,00,64,00,72,00,69,00,76,00,65,00,72,00,73,00,5c,00,76,00,69,00,6f,00,73,00,63,00,73,00,69,00,2e,00,73,00,79,00,73,00,00,00
		"DisplayName"="@oem0.inf,%VirtioScsi.SVCDESC%;Red Hat VirtIO SCSI pass-through Service"
		"Type"=dword:00000001
		"Start"=dword:00000000
		"ErrorControl"=dword:00000001
		"Owners"=hex(7):6f,00,65,00,6d,00,30,00,2e,00,69,00,6e,00,66,00,00,00,00,00
		"Group"="SCSI miniport"

		[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\vioscsi\Parameters]
		"BusType"=dword:0000000a

		[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\vioscsi\Parameters\PnpInterface]
		"5"=dword:00000001

		"""
	).lstrip().replace("\n", "\r\n")

	reg2 = inf_file.get_services_reg(
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1AF4",
			device_id="1004",
			subsystem_vendor_id="0008",
			subsystem_device_id="0007",
			revision="01",
		),
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		services_root=r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services",
	)
	assert reg == reg2

	reg = inf_file.get_services_reg(
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1AF4",
			device_id="1004",
			subsystem_vendor_id="0009",
			subsystem_device_id="0009",
			revision="99",
		),
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		services_root=r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services",
	)
	assert reg == reg2

	assert not inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86))
	assert not inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
		hardware_id=INFHardwareID(device_type=DeviceType.PCI, vendor_id="1AF4", device_id="1004"),
	)
	with pytest.raises(RuntimeError, match=r"No devices found for INFTargetOSVersion\(NTx86\) and INFHardwareID\(PCI\\VEN_1AF4&DEV_1004\)"):
		inf_file.get_services_reg(
			hardware_id=INFHardwareID(device_type=DeviceType.PCI, vendor_id="1AF4", device_id="1004"),
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
		)


def test_get_driver_database_reg_vioscsi_amd64() -> None:
	test_file = DATA_PATH / "vioscsi_amd64.inf"
	inf_file = INFFile(path=test_file, inf_name="vioscsi.inf")

	with mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(
				device_type=DeviceType.PCI,
				vendor_id="1AF4",
			),
		)
		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1004]
				"oem0.inf"=hex:02,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
				"oem0.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1048]
				"oem0.inf"=hex:02,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1048&SUBSYS_11001AF4&REV_01]
				"oem0.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\oem0.inf]
				@=hex(7):76,00,69,00,6f,00,73,00,63,00,73,00,69,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,35,00,38,00,30,00,61,00,32,00,36,00,32,00,62,00,66,00,64,00,38,00,35,00,33,00,34,00,34,00,62,00,00,00,00,00
				"Active"="vioscsi.inf_amd64_580a262bfd85344b"
				"Configurations"=hex(7):73,00,63,00,73,00,69,00,5f,00,69,00,6e,00,73,00,74,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b]
				"Version"=hex:00,ff,09,00,00,00,00,00,7b,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,40,c3,f9,31,9d,d7,01,40,51,68,00,55,00,64,00,00,00,00,00,00,00,00,00
				"Provider"="Red Hat, Inc."
				"InfName"="vioscsi.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="oem0.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst]
				"Service"="vioscsi"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Device]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Device\Interrupt Management]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Device\Interrupt Management\Affinity Policy]
				"DevicePolicy"=dword:00000005
				"DevicePriority"=dword:00000003

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Device\Interrupt Management\MessageSignaledInterruptProperties]
				"MSISupported"=dword:00000001
				"MessageNumberLimit"=dword:00000100

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Services\vioscsi]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Services\vioscsi\Parameters]
				"BusType"=dword:0000000a

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Configurations\scsi_inst\Services\vioscsi\Parameters\PnpInterface]
				"5"=dword:00000001

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors\PCI]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors\PCI\VEN_1AF4&DEV_1004]
				"Configuration"="scsi_inst"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO SCSI pass-through controller"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors\PCI\VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
				"Configuration"="scsi_inst"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO SCSI pass-through controller"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors\PCI\VEN_1AF4&DEV_1048]
				"Configuration"="scsi_inst"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO SCSI pass-through controller"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_amd64_580a262bfd85344b\Descriptors\PCI\VEN_1AF4&DEV_1048&SUBSYS_11001AF4&REV_01]
				"Configuration"="scsi_inst"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO SCSI pass-through controller"

			"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected

		with pytest.raises(RuntimeError, match=r"No devices found for INFTargetOSVersion\(NTx86\) and INFHardwareID\(PCI\\VEN_1AF4\)"):
			inf_file.get_driver_database_reg(
				target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
				hardware_id=INFHardwareID(
					device_type=DeviceType.PCI,
					vendor_id="1AF4",
				),
			)


def test_get_driver_database_reg_vioscsi_x86() -> None:
	test_file = DATA_PATH / "vioscsi_x86.inf"
	inf_file = INFFile(path=test_file, inf_name="vioscsi.inf")

	with mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
			hardware_id=INFHardwareID(
				device_type=DeviceType.PCI,
				vendor_id="1AF4",
			),
		)
		expected = (
			dedent(
				r"""
					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1004]
					"oem0.inf"=hex:02,ff,00,00

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
					"oem0.inf"=hex:01,ff,00,00

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1048]
					"oem0.inf"=hex:02,ff,00,00

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1048&SUBSYS_11001AF4&REV_01]
					"oem0.inf"=hex:01,ff,00,00

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\oem0.inf]
					@=hex(7):76,00,69,00,6f,00,73,00,63,00,73,00,69,00,2e,00,69,00,6e,00,66,00,5f,00,78,00,38,00,36,00,5f,00,39,00,32,00,31,00,65,00,65,00,39,00,34,00,62,00,39,00,32,00,32,00,35,00,37,00,39,00,31,00,39,00,00,00,00,00
					"Active"="vioscsi.inf_x86_921ee94b92257919"
					"Configurations"=hex(7):73,00,63,00,73,00,69,00,5f,00,69,00,6e,00,73,00,74,00,00,00,00,00

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919]
					"Version"=hex:00,ff,09,00,00,00,00,00,7b,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,c0,97,8c,0f,e7,d7,01,fc,53,68,00,5a,00,64,00,00,00,00,00,00,00,00,00
					"Provider"="Red Hat, Inc."
					"InfName"="vioscsi.inf"
					"OemPath"="opsi"
					"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
					"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
					"SignerScore"=dword:0d000005
					"StatusFlags"=dword:00000012
					@="oem0.inf"

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst]
					"Service"="vioscsi"
					"ConfigScope"=dword:00000007
					"ConfigFlags"=dword:00000000

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Device]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Device\Interrupt Management]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Device\Interrupt Management\Affinity Policy]
					"DevicePolicy"=dword:00000005
					"DevicePriority"=dword:00000003

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Device\Interrupt Management\MessageSignaledInterruptProperties]
					"MSISupported"=dword:00000001
					"MessageNumberLimit"=dword:00000100

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Services]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Services\vioscsi]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Services\vioscsi\Parameters]
					"BusType"=dword:0000000a

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Configurations\scsi_inst\Services\vioscsi\Parameters\PnpInterface]
					"5"=dword:00000001

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors\PCI]

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors\PCI\VEN_1AF4&DEV_1004]
					"Configuration"="scsi_inst"
					"Manufacturer"="Red Hat, Inc."
					"Description"="Red Hat VirtIO SCSI pass-through controller"

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors\PCI\VEN_1AF4&DEV_1004&SUBSYS_00081AF4&REV_00]
					"Configuration"="scsi_inst"
					"Manufacturer"="Red Hat, Inc."
					"Description"="Red Hat VirtIO SCSI pass-through controller"

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors\PCI\VEN_1AF4&DEV_1048]
					"Configuration"="scsi_inst"
					"Manufacturer"="Red Hat, Inc."
					"Description"="Red Hat VirtIO SCSI pass-through controller"

					[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioscsi.inf_x86_921ee94b92257919\Descriptors\PCI\VEN_1AF4&DEV_1048&SUBSYS_11001AF4&REV_01]
					"Configuration"="scsi_inst"
					"Manufacturer"="Red Hat, Inc."
					"Description"="Red Hat VirtIO SCSI pass-through controller"

			"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected

		with pytest.raises(RuntimeError, match=r"No devices found for INFTargetOSVersion\(NTamd64\) and INFHardwareID\(PCI\\VEN_1AF4\)"):
			inf_file.get_driver_database_reg(
				target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
				hardware_id=INFHardwareID(
					device_type=DeviceType.PCI,
					vendor_id="1AF4",
				),
			)


def test_parse_lsi_sas() -> None:
	filepath = DATA_PATH / "lsi_sas.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()
	assert inf_file._strings == {
		"DELL": "Dell",
		"DevDesc10": "LSI Adapter, SAS 3000 series, 8-port with 1068E",
		"DevDesc12": "LSI Adapter, SAS 3000 series, 4-port with 1064E",
		"DevDesc13": "LSI Adapter, SAS RAID-on-Chip, 8-port with 1078",
		"DevDesc8": "LSI Adapter, SAS 3000 series, 4-port with 1064",
		"DevDesc9": "LSI Adapter, SAS 3000 series, 8-port with 1068",
		"DevDescD1": "Dell SAS 5/E Adapter Controller",
		"DevDescD10": "Dell SAS 6/iR Integrated Workstation Controller",
		"DevDescD3": "Dell SAS 5/i Integrated Controller",
		"DevDescD4": "Dell SAS 5/iR Integrated Controller",
		"DevDescD6": "Dell SAS 5/iR Adapter Controller",
		"DevDescD7": "Dell SAS 6/iR Adapter Controller",
		"DevDescD8": "Dell SAS 6/iR Integrated Blades Controller",
		"DevDescD9": "Dell SAS 6/iR Integrated Controller",
		"LSI": "LSI",
		"REG_DWORD": "0x00010001",
		"REG_EXPAND_SZ": "0x00020000",
		"SERVICE_BOOT_START": "0",
		"SERVICE_ERROR_NORMAL": "1",
		"SERVICE_KERNEL_DRIVER": "1",
		"SPSVCINST_ASSOCSERVICE": "0x00000002",
	}

	assert inf_file.version and inf_file.version.Class == "SCSIAdapter"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86), manufacturer="LSI")
	assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
		r"PCI\VEN_1000&DEV_0054",
		r"PCI\VEN_1000&DEV_0058",
		r"PCI\VEN_1000&DEV_0056",
	]

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64), manufacturer="LSI")
	assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
		r"PCI\VEN_1000&DEV_0050",
		r"PCI\VEN_1000&DEV_0054",
		r"PCI\VEN_1000&DEV_0056",
	]

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.IA64), manufacturer="LSI")
	assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
		r"PCI\VEN_1000&DEV_0050",
		r"PCI\VEN_1000&DEV_0054",
		r"PCI\VEN_1000&DEV_0058",
		r"PCI\VEN_1000&DEV_0062",
	]

	for arch in (Architecture.X86, Architecture.X64, Architecture.IA64):
		devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch), manufacturer="DELL")
		assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
			r"PCI\VEN_1000&DEV_0054&SUBSYS_1F041028",
			r"PCI\VEN_1000&DEV_0054&SUBSYS_1F061028",
			r"PCI\VEN_1000&DEV_0054&SUBSYS_1F071028",
			r"PCI\VEN_1000&DEV_0054&SUBSYS_1F081028",
			r"PCI\VEN_1000&DEV_0054&SUBSYS_1F091028",
			r"PCI\VEN_1000&DEV_0058&SUBSYS_1F0E1028",
			r"PCI\VEN_1000&DEV_0058&SUBSYS_1F0F1028",
			r"PCI\VEN_1000&DEV_0058&SUBSYS_1F101028",
			r"PCI\VEN_1000&DEV_0058&SUBSYS_021D1028",
		]


def test_parse_ser2pl() -> None:
	filepath = DATA_PATH / "ser2pl.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Ports"

	for arch in (Architecture.X86, Architecture.X64, Architecture.IA64):
		devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))
		assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
			r"USB\VID_067B&PID_2303",
		]
		for dev in devs:
			assert dev.manufacturer == "Prolific"


def test_parse_vioinput() -> None:
	filepath = DATA_PATH / "vioinput.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "HIDClass"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_1AF4&DEV_1052&SUBSYS_11001AF4&REV_01",
		r"VIOINPUT\REV_01",
	]


def test_parse_qemupciserial() -> None:
	filepath = DATA_PATH / "qemupciserial.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "MultiFunction"

	for arch in (Architecture.X86, Architecture.X64):
		assert inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	for arch in (Architecture.X86, Architecture.X64):
		devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

		assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
			r"PCI\VEN_1B36&DEV_0002",
			r"PCI\VEN_1B36&DEV_0003",
			r"PCI\VEN_1B36&DEV_0004",
		]


def test_parse_pvpanic() -> None:
	filepath = DATA_PATH / "pvpanic.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "System"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [r"ACPI\QEMU0001"]


def test_parse_pvscsi() -> None:
	filepath = DATA_PATH / "pvscsi.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()
	assert inf_file._strings == {
		"pvscsi.installers.value.name": "vwdk.installers",
		"pvscsi.installers.value.windows": "Windows",
		"pvscsi.DiskName": "pvscsi Storage Controller Driver",
		"VMWARE": "VMware, Inc.",
		"DEVICE": "VMware PVSCSI Controller",
		"DSKID1": "VMware PVSCSI Controller Installation Disk 1",
		"FLG_ADDREG_KEYONLY": "0x00000010",
		"FLG_ADDREG_TYPE_DWORD": "0x00010001",
		"FLG_ADDREG_TYPE_EXPAND_SZ": "0x00020000",
		"FLG_DELREG_MULTI_SZ_DELSTRING": "0x00018002",
	}

	assert inf_file.version and inf_file.version.Class == "SCSIAdapter"

	for arch in (Architecture.X86, Architecture.IA64):
		assert not inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64), manufacturer="VMware, Inc.")
	assert [hwid.to_string() for dev in devs for hwid in dev.hardware_ids] == [
		r"PCI\VEN_15AD&DEV_07C0",
	]


def test_viostor() -> None:
	filepath = DATA_PATH / "viostor.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "SCSIAdapter"

	for arch in (Architecture.X86, Architecture.IA64):
		assert not inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_1AF4&DEV_1001&SUBSYS_00021AF4&REV_00",
		r"PCI\VEN_1AF4&DEV_1042&SUBSYS_11001AF4&REV_01",
	]
	assert [hwid.to_string() for dev in devs for hwid in dev.compatible_ids] == [
		r"PCI\VEN_1AF4&DEV_1001",
		r"PCI\VEN_1AF4&DEV_1042",
	]

	reg = inf_file.get_services_reg(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		hardware_id=INFHardwareID(device_type="PCI", vendor_id="1AF4", device_id="1001"),
		oem_inf_name="viostor.inf",
	)

	assert reg == dedent(
		r"""
		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor]
		"ImagePath"=hex(2):73,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,00,5c,00,64,00,72,00,69,00,76,00,65,00,72,00,73,00,5c,00,76,00,69,00,6f,00,73,00,74,00,6f,00,72,00,2e,00,73,00,79,00,73,00,00,00
		"DisplayName"="@viostor.inf,;"
		"Type"=dword:00000001
		"Start"=dword:00000000
		"ErrorControl"=dword:00000001
		"Owners"=hex(7):76,00,69,00,6f,00,73,00,74,00,6f,00,72,00,2e,00,69,00,6e,00,66,00,00,00,00,00
		"Group"="SCSI miniport"

		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters]
		"BusType"=dword:00000001

		[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\viostor\Parameters\PnpInterface]
		"5"=dword:00000001

		"""
	).lstrip().replace("\n", "\r\n")


def test_parse_dax3_ext_rtk() -> None:
	filepath = DATA_PATH / "dax3_ext_rtk.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Extension"

	for arch in (Architecture.X86, Architecture.IA64):
		assert not inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1282",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1282",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC128E",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC128E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC121E",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC121E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12D2",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12D2",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC120A",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC120A",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC123E",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC123E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC122E",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC122E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1290",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1290",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC129C",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC129C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1284",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1284",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1248",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1248",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC121C",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC121C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC123C",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC123C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC122A",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC122A",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0298&SUBSYS_10EC12BA",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0298&SUBSYS_10EC12BA",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12B8",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12B8",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1216",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1216",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC126A",
		r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC126A",
	]


def test_get_reg_pvscsi() -> None:
	filepath = DATA_PATH / "pvscsi.inf"
	inf_file = INFFile(filepath)
	with mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(
				device_type=DeviceType.PCI,
				vendor_id="15AD",
			),
			oem_inf_name="pvscsi.inf",
		)

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_15AD&DEV_07C0]
				"pvscsi.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\pvscsi.inf]
				@=hex(7):70,00,76,00,73,00,63,00,73,00,69,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,38,00,39,00,64,00,63,00,32,00,39,00,35,00,65,00,62,00,65,00,30,00,30,00,36,00,63,00,36,00,00,00,00,00
				"Active"="pvscsi.inf_amd64_89dc295ebe006c6"
				"Configurations"=hex(7):64,00,64,00,69,00,6e,00,73,00,74,00,61,00,6c,00,6c,00,2e,00,6e,00,74,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6]
				"Version"=hex:00,ff,09,00,00,00,00,00,7b,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,00,2f,a0,91,2e,d8,01,00,00,19,00,03,00,01,00,00,00,00,00,00,00,00,00
				"Provider"="VMware, Inc."
				"InfName"="pvscsi.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="pvscsi.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt]
				"Service"="pvscsi"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Device]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Device\Interrupt Management]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Device\Interrupt Management\MessageSignaledInterruptProperties]
				"MSISupported"=dword:00000001
				"MessageNumberLimit"=dword:00000001

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Services\pvscsi]
				"vwdk.installers"=hex(7):57,00,69,00,6e,00,64,00,6f,00,77,00,73,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Services\pvscsi\Parameters]
				"BusType"=dword:0000000a

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Configurations\ddinstall.nt\Services\pvscsi\Parameters\PnpInterface]
				"5"=dword:00000001

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Descriptors\PCI]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\pvscsi.inf_amd64_89dc295ebe006c6\Descriptors\PCI\VEN_15AD&DEV_07C0]
				"Configuration"="ddinstall.nt"
				"Manufacturer"="VMware, Inc."
				"Description"="VMware PVSCSI Controller"

				""",
			)
			.lstrip()
			.replace("\n", "\r\n")
		)

		assert reg == expected


def test_get_reg_netkvm() -> None:
	filepath = DATA_PATH / "netkvm.inf"
	inf_file = INFFile(filepath)
	with mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(
				device_type=DeviceType.PCI,
				vendor_id="1AF4",
			),
			oem_inf_name="netkvm.inf",
		)

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1000]
				"netkvm.inf"=hex:02,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1000&SUBSYS_00011AF4&REV_00]
				"netkvm.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1041]
				"netkvm.inf"=hex:02,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_1AF4&DEV_1041&SUBSYS_11001AF4&REV_01]
				"netkvm.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\netkvm.inf]
				@=hex(7):6e,00,65,00,74,00,6b,00,76,00,6d,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,32,00,66,00,39,00,39,00,65,00,32,00,39,00,64,00,37,00,63,00,62,00,61,00,34,00,33,00,39,00,34,00,00,00,00,00
				"Active"="netkvm.inf_amd64_2f99e29d7cba4394"
				"Configurations"=hex(7):6b,00,76,00,6d,00,6e,00,65,00,74,00,36,00,2e,00,6e,00,64,00,69,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394]
				"Version"=hex:00,ff,09,00,00,00,00,00,72,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,00,95,75,95,b2,d8,01,e4,57,68,00,5b,00,64,00,00,00,00,00,00,00,00,00
				"Provider"="Red Hat, Inc."
				"InfName"="netkvm.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="netkvm.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi]
				"Service"="netkvm"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device]
				"BusNumber"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Interrupt Management\Affinity Policy]
				"DevicePolicy"=dword:00000000
				"DevicePriority"=dword:00000002

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Interrupt Management\MessageSignaledInterruptProperties]
				"MSISupported"=dword:00000001
				"MessageNumberLimit"=dword:00000800

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi]
				"Service"="netkvm"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Interfaces]
				"UpperRange"="ndis5"
				"LowerRange"="ethernet"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*IPChecksumOffloadIPv4]
				"ParamDesc"="IPv4 Checksum Offload"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*IPChecksumOffloadIPv4\enum]
				"3"="Rx & Tx Enabled"
				"2"="Rx Enabled"
				"1"="Tx Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*LsoV2IPv4]
				"ParamDesc"="Large Send Offload V2 (IPv4)"
				"Default"="1"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*LsoV2IPv4\enum]
				"1"="Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*LsoV2IPv6]
				"ParamDesc"="Large Send Offload V2 (IPv6)"
				"Default"="1"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*LsoV2IPv6\enum]
				"1"="Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*PriorityVLANTag]
				"ParamDesc"="Priority and VLAN tagging"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*PriorityVLANTag\enum]
				"3"="All"
				"2"="VLan"
				"1"="Priority"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*TCPChecksumOffloadIPv4]
				"ParamDesc"="TCP Checksum Offload (IPv4)"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*TCPChecksumOffloadIPv4\enum]
				"3"="Rx & Tx Enabled"
				"2"="Rx Enabled"
				"1"="Tx Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*TCPChecksumOffloadIPv6]
				"ParamDesc"="TCP Checksum Offload (IPv6)"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*TCPChecksumOffloadIPv6\enum]
				"3"="Rx & Tx Enabled"
				"2"="Rx Enabled"
				"1"="Tx Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*UDPChecksumOffloadIPv4]
				"ParamDesc"="UDP Checksum Offload (IPv4)"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*UDPChecksumOffloadIPv4\enum]
				"3"="Rx & Tx Enabled"
				"2"="Rx Enabled"
				"1"="Tx Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*UDPChecksumOffloadIPv6]
				"ParamDesc"="UDP Checksum Offload (IPv6)"
				"Default"="3"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\*UDPChecksumOffloadIPv6\enum]
				"3"="Rx & Tx Enabled"
				"2"="Rx Enabled"
				"1"="Tx Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\DoLog]
				"ParamDesc"="Logging.Enable"
				"Default"="1"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\DoLog\enum]
				"1"="Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.RxCS]
				"ParamDesc"="%OffLoad.RxCS%"
				"Default"="31"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.RxCS\enum]
				"31"="All"
				"27"="TCP/UDP(v4"
				"3"="TCP/UDP(v4)"
				"1"="TCP(v4)"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.TxChecksum]
				"ParamDesc"="%OffLoad.TxChecksum%"
				"Default"="31"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.TxChecksum\enum]
				"31"="All"
				"27"="TCP/UDP(v4"
				"3"="TCP/UDP(v4)"
				"1"="TCP(v4)"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.TxLSO]
				"ParamDesc"="%OffLoad.TxLSO%"
				"Default"="2"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\OffLoad.TxLSO\enum]
				"2"="Maximal"
				"1"="IPv4"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\Priority]
				"ParamDesc"="Init.Do802.1PQ"
				"Default"="1"
				"type"="enum"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\Priority\enum]
				"1"="Enabled"
				"0"="Disabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\RxCapacity\enum]
				"16"="16"
				"32"="32"
				"64"="64"
				"128"="128"
				"256"="256"
				"512"="512"
				"1024"="1024"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\Params\TxCapacity\enum]
				"16"="16"
				"32"="32"
				"64"="64"
				"128"="128"
				"256"="256"
				"512"="512"
				"1024"="1024"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*JumboPacket]
				"ParamDesc"="Jumbo Packet"
				"type"="long"
				"default"="1514"
				"min"="590"
				"max"="65500"
				"step"="1"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*NumRssQueues]
				"ParamDesc"="Maximum Number of RSS Queues"
				"type"="int"
				"default"="16"
				"min"="1"
				"max"="32"
				"step"="1"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RSS]
				"ParamDesc"="Receive Side Scaling"
				"Type"="enum"
				"Default"="1"
				"Optional"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RSS\enum]
				"0"="Disabled"
				"1"="Enabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RscIPv4]
				"ParamDesc"="Recv Segment Coalescing (IPv4)"
				"Type"="enum"
				"Default"="1"
				"Optional"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RscIPv4\enum]
				"0"="Disabled"
				"1"="Enabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RscIPv6]
				"ParamDesc"="Recv Segment Coalescing (IPv6)"
				"Type"="enum"
				"Default"="1"
				"Optional"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*RscIPv6\enum]
				"0"="Disabled"
				"1"="Enabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*UsoIPv4]
				"ParamDesc"="UDP Segmentation Offload (IPv4)"
				"Type"="enum"
				"Default"="1"
				"Optional"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*UsoIPv4\enum]
				"0"="Disabled"
				"1"="Enabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*UsoIPv6]
				"ParamDesc"="UDP Segmentation Offload (IPv6)"
				"Type"="enum"
				"Default"="1"
				"Optional"="0"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\*UsoIPv6\enum]
				"0"="Disabled"
				"1"="Enabled"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\DebugLevel]
				"ParamDesc"="Logging.Level"
				"type"="int"
				"default"="0"
				"min"="0"
				"max"="8"
				"step"="1"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\NetworkAddress]
				"ParamDesc"="Assign MAC"
				"type"="edit"
				"Optional"="1"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\RxCapacity]
				"ParamDesc"="Init.MaxRxBuffers"
				"type"="enum"
				"default"="256"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\TxCapacity]
				"ParamDesc"="Init.MaxTxBuffers"
				"type"="enum"
				"default"="1024"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Device\Ndi\params\VlanID]
				"ParamDesc"="VLan ID"
				"type"="long"
				"default"="0"
				"min"="0"
				"max"="4094"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Services\netkvm]
				"TextModeFlags"=dword:00000001

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Configurations\kvmnet6.ndi\Services\netkvm\Parameters]
				"DisableMSI"="0"
				"EarlyDebug"="3"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors\PCI]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors\PCI\VEN_1AF4&DEV_1000]
				"Configuration"="kvmnet6.ndi"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO Ethernet Adapter"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors\PCI\VEN_1AF4&DEV_1000&SUBSYS_00011AF4&REV_00]
				"Configuration"="kvmnet6.ndi"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO Ethernet Adapter"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors\PCI\VEN_1AF4&DEV_1041]
				"Configuration"="kvmnet6.ndi"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO Ethernet Adapter"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\netkvm.inf_amd64_2f99e29d7cba4394\Descriptors\PCI\VEN_1AF4&DEV_1041&SUBSYS_11001AF4&REV_01]
				"Configuration"="kvmnet6.ndi"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO Ethernet Adapter"

			"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected


def test_devices_netkvm() -> None:
	filepath = DATA_PATH / "netkvm.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Net"

	for arch in (Architecture.X86, Architecture.IA64):
		assert not inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_1AF4&DEV_1000&SUBSYS_00011AF4&REV_00",
		r"PCI\VEN_1AF4&DEV_1041&SUBSYS_11001AF4&REV_01",
	]
	assert [hwid.to_string() for dev in devs for hwid in dev.compatible_ids] == [
		r"PCI\VEN_1AF4&DEV_1000",
		r"PCI\VEN_1AF4&DEV_1041",
	]

	assert inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1AF4",
			device_id="1000",
			subsystem_vendor_id="1AF4",
			subsystem_device_id="0001",
			revision="00",
		),
	)
	assert inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1AF4",
			device_id="1041",
			subsystem_vendor_id="1AF4",
			subsystem_device_id="1100",
			revision="01",
		),
	)
	assert inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1af4",
			device_id="1000",
		),
	)
	assert not inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
		hardware_id=INFHardwareID(
			device_type=DeviceType.PCI,
			vendor_id="1af4",
			device_id="1001",
		),
	)
	# Version
	assert inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert not inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=5))
	assert not inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=2)
	)
	assert inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6))
	assert inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=3))
	assert inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=6, OSMinorVersion=4))
	assert inf_file.is_compatible(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=10))
	assert inf_file.is_compatible(
		target_os_version=INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=19041)
	)


def test_devices_storufs() -> None:
	filepath = DATA_PATH / "storufs.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "SCSIAdapter"

	for arch in (Architecture.X86, Architecture.IA64):
		assert not inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=arch))

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\CC_010901",
		r"ACPI\CC_010901",
		r"PCI\VEN_8086&DEV_0ACE&SUBSYS_72708086&REV_01",
		r"PCI\VEN_8086&DEV_1ACE",
		r"PCI\VEN_8086&DEV_98FA&SUBSYS_72708086",
		r"PCI\VEN_8086&DEV_A0FA&SUBSYS_72708086&REV_00",
		r"PCI\VEN_8086&DEV_4B43&SUBSYS_72708086",
		r"PCI\VEN_8086&DEV_4B41&SUBSYS_72708086",
		r"PCI\VEN_8086&DEV_51FF",
		r"PCI\VEN_8086&DEV_51FA",
		r"PCI\VEN_8086&DEV_54FF",
		r"ACPI\QCOM24A5",
		r"PCI\VEN_1179&DEV_7012&REV_00",
	]


def test_devices_hid_pci() -> None:
	filepath = DATA_PATH / "HID_PCI.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "HIDClass"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"{DEA5AE2A-D1FD-438A-A091-CBD484788436}\ISH_MINIPORT",
	]


def test_devices_surface_pen() -> None:
	filepath = DATA_PATH / "SurfacePen217Integration.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "HIDClass"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"HID\{00001812-0000-1000-8000-00805f9b34fb}_Dev_VID&02045e_PID&0921&Col02",
	]


def test_devices_iigd_ext_lx() -> None:
	filepath = DATA_PATH / "iigd_ext_lx.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Extension"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_46D0&SUBSYS_00791414",
		r"PCI\VEN_8086&DEV_46D1&SUBSYS_00791414",
		r"PCI\VEN_8086&DEV_46D2&SUBSYS_00791414",
	]


def test_devices_surface_oem_panel() -> None:
	filepath = DATA_PATH / "SurfaceOemPanel.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Monitor"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"Monitor\LGD0554",
		r"Monitor\LGD0555",
		r"Monitor\SHP14B3",
		r"Monitor\SHP14B4",
		r"Monitor\JDI0000",
		r"Monitor\MEI96A2",
		r"Monitor\SHP1509",
		r"Monitor\LGD06B1",
		r"Monitor\LGD06B2",
		r"Monitor\LGD0719",
		r"Monitor\BOE0AA4",
		r"Monitor\BOE088B",
		r"Monitor\SHP1572",
	]


def test_devices_surface_oem_panel_customization() -> None:
	filepath = DATA_PATH / "SurfaceOemPanelCustomization.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Extension"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"Monitor\BOE088B",
	]


def test_devices_surface_oem_panel_ehdxacpm() -> None:
	filepath = DATA_PATH / "EHDXACPM.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "MEDIA"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1220",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC122C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1292",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1294",
	]


def test_devices_surface_oem_panel_netwtw08() -> None:
	filepath = DATA_PATH / "Netwtw08.INF"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "net"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_02F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_06F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_00808086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_00848086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_00888086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_008C8086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_16531A56",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_16541A56",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_20808086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_40808086",
		r"PCI\VEN_8086&DEV_2723&SUBSYS_40888086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_2726&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_34F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_3DF0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_43F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_4DF0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_51F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_51F1&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_54F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_7A70&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_7AF0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_7F70&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00708086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00748086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00788086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_007C8086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02448086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02748086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_16511A56",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_16521A56",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_20748086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_40708086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_42448086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_42748086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_A0F0&SUBSYS_60748086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00148086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00188086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_001C8086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00608086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02148086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_15501A56",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_40108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_40188086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_401C8086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_60108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_60148086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_80108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_80148086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_A0148086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_E0108086",
		r"PCI\VEN_8086&DEV_2526&SUBSYS_E0148086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00608086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_30DC&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00608086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_31DC&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00608086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_9DF0&SUBSYS_42A48086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00308086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00348086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00388086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_003C8086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00608086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00648086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00A08086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_00A48086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02308086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02348086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02388086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_023C8086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02608086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02648086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02A08086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_02A48086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_15511A56",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_15521A56",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_20308086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_20348086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_40308086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_40348086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_40A48086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_42348086",
		r"PCI\VEN_8086&DEV_A370&SUBSYS_42A48086",
	]


@pytest.mark.parametrize(
	"build_number, expected_configuration",
	(
		(10240, None),  # Windows 10 version 1507
		(18362, "intcazaudmodel_sb_win10.ntamd64"),  # Windows 10 version 1903
		(19045, "intcazaudmodel_sb_win10.ntamd64"),  # Windows 10 version 22H2
		(22000, "intcazaudmodel_sb_win11.ntamd64"),  # Windows 11 version 21H2
		(22631, "intcazaudmodel_sb_win11.ntamd64"),  # Windows 11 version 23H2
	),
)
def test_devices_ehdxsstmd3a4(build_number: int, expected_configuration: str) -> None:
	filepath = DATA_PATH / "EHDXSSTMD3A4.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "MEDIA"

	target_os_version = INFTargetOSVersion(Architecture=Architecture.X64, OSMajorVersion=10, OSMinorVersion=0, BuildNumber=build_number)
	devs = inf_file.get_devices(target_os_version=target_os_version)
	if expected_configuration:
		assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
			r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1288",
			r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1288",
			r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1286",
			r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1286",
			r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1284",
			r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC1284",
			r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12D2",
			r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0274&SUBSYS_10EC12D2",
		]
		for dev in devs:
			assert dev.configuration == expected_configuration
	else:
		assert not devs


def test_devices_iactrllogic64() -> None:
	filepath = DATA_PATH / "iactrllogic64.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "System"

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"ACPI\INT3472",
		r"ACPI\INT346F",
	]
	for dev in devs:
		assert dev.hardware_id and dev.hardware_id.vendor_id == "INT"


def test_hdxacpdellcsmb() -> None:
	filepath = DATA_PATH / "HDXACPDELLCSMB.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert (
		inf_file.version
		and inf_file.version.Class == "MEDIA"
		and inf_file.version.DriverVer.version == (6, 0, 9514, 1)
		and inf_file.version.DriverVer.date == datetime(2023, 5, 9, tzinfo=timezone.utc)
	)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_102809E3",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A11",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A12",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A16",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A1D",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A1E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280A6E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280A6F",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280A97",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280AB4",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280AB5",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A77",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A78",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A79",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A7A",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280A8C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B59",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B5E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B5D",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B5B",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BFD",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BFE",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BFF",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C4A",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C4B",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C4C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280C55",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280C56",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280C57",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B38",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B46",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B7E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B47",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B7F",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B48",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B84",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B85",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B86",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B87",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C23",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C24",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C25",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C26",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C27",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C21",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C22",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B6E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280B6F",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B6B",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B6C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B6D",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B7B",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B7C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B7D",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280B9F",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BA0",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BA1",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BA2",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BA3",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280BA4",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280C3E",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0236&SUBSYS_10280C3F",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C38",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C3A",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C3C",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C39",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C3B",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0295&SUBSYS_10280C3D",
		r"HDAUDIO\FUNC_01&VEN_10EC&DEV_0289&SUBSYS_10280C4D",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(
				device_type=DeviceType.HDAUDIO,
				device_id="0289",
			),
			oem_inf_name="HDXACPDELLCSMB.inf",
		)
		assert '"UsePositionLock"=hex:01,00,00,00' in reg


def test_ude() -> None:
	filepath = DATA_PATH / "Ude.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert (
		inf_file.version
		and inf_file.version.Class == "System"
		and inf_file.version.DriverVer.date.isoformat() == "2023-01-14T00:00:00+00:00"
		and inf_file.version.DriverVer.version == (0, 5, 100, 871)
	)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_7560&SUBSYS_58231028",
		r"PCI\VEN_8086&DEV_7560&SUBSYS_3A171028",
		r"PCI\VEN_8086&DEV_7560&SUBSYS_00000000",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(
				device_type="PCI",
				subsystem_vendor_id="1028",
				subsystem_device_id="5823",
			),
			oem_inf_name="Ude.inf",
		)
		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_8086&DEV_7560&SUBSYS_58231028]
				"Ude.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\Ude.inf]
				@=hex(7):75,00,64,00,65,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,30,00,30,00,62,00,63,00,36,00,31,00,34,00,65,00,00,00,00,00
				"Active"="ude.inf_amd64_00bc614e"
				"Configurations"=hex(7):75,00,64,00,65,00,5f,00,65,00,73,00,69,00,6d,00,5f,00,64,00,65,00,76,00,69,00,63,00,65,00,2e,00,6e,00,74,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e]
				"Version"=hex:00,ff,09,00,00,00,00,00,7d,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,c0,21,25,ab,27,d9,01,67,03,64,00,05,00,00,00,00,00,00,00,00,00,00,00
				"Provider"="Fibocom Wireless Inc."
				"InfName"="ude.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="Ude.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations\ude_esim_device.nt]
				"Service"="UDE"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations\ude_esim_device.nt\Device]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations\ude_esim_device.nt\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations\ude_esim_device.nt\Services\ModemAuthenticatorService]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Configurations\ude_esim_device.nt\Services\UDE]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Descriptors\PCI]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\ude.inf_amd64_00bc614e\Descriptors\PCI\VEN_8086&DEV_7560&SUBSYS_58231028]
				"Configuration"="ude_esim_device.nt"
				"Manufacturer"="Fibocom Wireless Inc."
				"Description"="DW5823e-eSIM Intel(R) XMM7560 R+ LTE-A UDE Device"

				"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected


def test_hdbusext() -> None:
	filepath = DATA_PATH / "HdBusExt.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert (
		inf_file.version
		and inf_file.version.Class == "Extension"
		and inf_file.version.DriverVer.date.isoformat() == "2023-02-22T00:00:00+00:00"
		and inf_file.version.DriverVer.version == (31, 0, 101, 4146)
	)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_A0C8",
		r"PCI\VEN_8086&DEV_43C8",
		r"PCI\VEN_8086&DEV_7AD0",
		r"PCI\VEN_8086&DEV_7AD1",
		r"PCI\VEN_8086&DEV_7AD2",
		r"PCI\VEN_8086&DEV_7AD3",
		r"PCI\VEN_8086&DEV_7AD4",
		r"PCI\VEN_8086&DEV_7AD5",
		r"PCI\VEN_8086&DEV_7AD6",
		r"PCI\VEN_8086&DEV_7AD7",
		r"PCI\VEN_8086&DEV_51C8",
		r"PCI\VEN_8086&DEV_51C9",
		r"PCI\VEN_8086&DEV_51CC",
		r"PCI\VEN_8086&DEV_51CD",
		r"PCI\VEN_8086&DEV_54C8",
		r"PCI\VEN_8086&DEV_54C9",
		r"PCI\VEN_8086&DEV_54CA",
		r"PCI\VEN_8086&DEV_54CB",
		r"PCI\VEN_8086&DEV_54CC",
		r"PCI\VEN_8086&DEV_54CD",
		r"PCI\VEN_8086&DEV_54CE",
		r"PCI\VEN_8086&DEV_54CF",
		r"PCI\VEN_8086&DEV_7A50",
		r"PCI\VEN_8086&DEV_7A51",
		r"PCI\VEN_8086&DEV_7A52",
		r"PCI\VEN_8086&DEV_7A53",
		r"PCI\VEN_8086&DEV_7A54",
		r"PCI\VEN_8086&DEV_7A55",
		r"PCI\VEN_8086&DEV_7A56",
		r"PCI\VEN_8086&DEV_7A57",
		r"PCI\VEN_8086&DEV_51CA",
		r"PCI\VEN_8086&DEV_51CB",
		r"PCI\VEN_8086&DEV_51CE",
		r"PCI\VEN_8086&DEV_51CF",
		r"PCI\VEN_8086&DEV_F1C8",
		r"PCI\VEN_8086&DEV_490D",
		r"PCI\VEN_8086&DEV_4F90",
		r"PCI\VEN_8086&DEV_4F91",
		r"PCI\VEN_8086&DEV_4F92",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(device_type="PCI", vendor_id="8086", device_id="4F91"),
			oem_inf_name="HdBusExt.inf",
		)

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\PCI\VEN_8086&DEV_4F91]
				"HdBusExt.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\HdBusExt.inf]
				@=hex(7):68,00,64,00,62,00,75,00,73,00,65,00,78,00,74,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,30,00,30,00,62,00,63,00,36,00,31,00,34,00,65,00,00,00,00,00
				"Active"="hdbusext.inf_amd64_00bc614e"
				"Configurations"=hex(7):69,00,61,00,75,00,64,00,69,00,6f,00,5f,00,77,00,31,00,30,00,5f,00,64,00,33,00,63,00,6f,00,6c,00,64,00,5f,00,64,00,73,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e]
				"Version"=hex:00,ff,09,00,00,00,00,00,e7,4c,f8,e2,fa,8e,1c,41,aa,69,97,45,4c,a4,cb,57,00,00,3e,9b,50,46,d9,01,32,10,65,00,00,00,1f,00,00,00,00,00,00,00,00,00
				"Provider"="Intel Corporation"
				"InfName"="hdbusext.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="HdBusExt.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Configurations\iaudio_w10_d3cold_ds]
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Configurations\iaudio_w10_d3cold_ds\Device]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Configurations\iaudio_w10_d3cold_ds\Device\PowerSettings]
				"EnableD3Cold"=dword:00000001

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Configurations\iaudio_w10_d3cold_ds\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Descriptors\PCI]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\hdbusext.inf_amd64_00bc614e\Descriptors\PCI\VEN_8086&DEV_4F91]
				"Configuration"="iaudio_w10_d3cold_ds"
				"Manufacturer"="Intel Corporation"
				"Description"="Intel(R) HD Graphics D3COLD"

				"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)

		assert reg == expected


def test_rtdusbad_dell() -> None:
	filepath = DATA_PATH / "RtDUsbAD_dell.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "MEDIA" and inf_file.version.DriverVer.version == (6, 3, 9600, 2330)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"USB\VID_0BDA&PID_4001",
		r"USB\VID_0BDA&PID_4008",
		r"USB\VID_0BDA&PID_400E",
		r"USB\VID_0BDA&PID_4014",
		r"USB\VID_0BDA&PID_4016",
		r"USB\VID_0BDA&PID_402D",
		r"USB\VID_0BDA&PID_402E",
		r"USB\VID_0BDA&PID_4C63",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(device_type="USB", vendor_id="0BDA", device_id="4016"),
			oem_inf_name="RtDUsbAD_dell.inf",
		)

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\USB\VID_0BDA&PID_4016]
				"RtDUsbAD_dell.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\RtDUsbAD_dell.inf]
				@=hex(7):72,00,74,00,64,00,75,00,73,00,62,00,61,00,64,00,5f,00,64,00,65,00,6c,00,6c,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,30,00,30,00,62,00,63,00,36,00,31,00,34,00,65,00,00,00,00,00
				"Active"="rtdusbad_dell.inf_amd64_00bc614e"
				"Configurations"=hex(7):72,00,74,00,6b,00,75,00,73,00,62,00,61,00,64,00,2e,00,6e,00,74,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e]
				"Version"=hex:00,ff,09,00,00,00,00,00,6c,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,80,ed,2c,4b,8b,d8,01,1a,09,80,25,03,00,06,00,00,00,00,00,00,00,00,00
				"Provider"="Realtek Semiconductor Corp."
				"InfName"="rtdusbad_dell.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="RtDUsbAD_dell.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt]
				"Service"="RtkUsbAD_2330"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device]
				"SetupPreferredAudioDevices"=hex:01,00,00,00
				"AssociatedFilters"="wdmaud"
				"Driver"="RtUsbA64.sys"
				"DriverInstallPath"="%13%"
				"CLSID"="{17CCA71B-ECD7-11D0-B908-00A0C9223196}"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers]
				"SubClasses"="wave"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\aux\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\midi\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\mixer\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\wave\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Services\RtkUsbAD_2330]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors\USB]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors\USB\VID_0BDA&PID_4016]
				"Configuration"="rtkusbad.nt"
				"Manufacturer"="Realtek"
				"Description"="Realtek USB Audio"

				"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected


def test_vioprot() -> None:
	filepath = DATA_PATH / "vioprot.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "NetTrans" and inf_file.version.DriverVer.version == (100, 95, 104, 26200)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"VIOPROT",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		with pytest.raises(RuntimeError, match=r"No devices found for INFTargetOSVersion\(NTamd64\) and INFHardwareID\(VIOPROT\)"):
			inf_file.get_driver_database_reg(
				target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
				hardware_id=INFHardwareID(device_type="VIOPROT"),
				oem_inf_name="vioprot.inf",
			)
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
			hardware_id=INFHardwareID(device_type="VIOPROT"),
			oem_inf_name="vioprot.inf",
		)

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\VIOPROT]
				"vioprot.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\vioprot.inf]
				@=hex(7):76,00,69,00,6f,00,70,00,72,00,6f,00,74,00,2e,00,69,00,6e,00,66,00,5f,00,78,00,38,00,36,00,5f,00,30,00,30,00,62,00,63,00,36,00,31,00,34,00,65,00,00,00,00,00
				"Active"="vioprot.inf_x86_00bc614e"
				"Configurations"=hex(7):69,00,6e,00,73,00,74,00,61,00,6c,00,6c,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e]
				"Version"=hex:00,ff,09,00,00,00,00,00,75,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,c0,80,ef,49,d6,da,01,58,66,68,00,5f,00,64,00,00,00,00,00,00,00,00,00
				"Provider"="Red Hat, Inc."
				"InfName"="vioprot.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="vioprot.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install]
				"Service"="netkvmp"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install\Device]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install\Device\Ndi]
				"ClsID"="{F69513F1-8E1A-4F35-82D9-046406970E6D}"
				"Service"="netkvmp"
				"HelpText"="A driver to support SRIOV Failover for VirtIO network devices"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install\Device\Ndi\Interfaces]
				"UpperRange"="noupper"
				"LowerRange"="ndis5"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Configurations\install\Services\netkvmp]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\vioprot.inf_x86_00bc614e\Descriptors\VIOPROT]
				"Configuration"="install"
				"Manufacturer"="Red Hat, Inc."
				"Description"="Red Hat VirtIO NetKVM Protocol Driver"

				"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected

		reg = inf_file.get_services_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X86),
			hardware_id=INFHardwareID(device_type="VIOPROT"),
			oem_inf_name="vioprot.inf",
		)
		assert reg == dedent(
			r"""
			[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\netkvmp]
			"ImagePath"=hex(2):73,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,00,5c,00,6e,00,65,00,74,00,6b,00,76,00,6d,00,70,00,73,00,2e,00,65,00,78,00,65,00,00,00
			"DisplayName"="@vioprot.inf,%NETKVMP_Desc%;Red Hat VirtIO NetKVM Protocol Driver"
			"Type"=dword:00000010
			"Start"=dword:00000002
			"ErrorControl"=dword:00000001
			"Owners"=hex(7):76,00,69,00,6f,00,70,00,72,00,6f,00,74,00,2e,00,69,00,6e,00,66,00,00,00,00,00

			"""
		).lstrip().replace("\n", "\r\n")


def test_e1d68x64() -> None:
	filepath = DATA_PATH / "e1d68x64.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert (
		inf_file.version
		and inf_file.version.Class == "Net"
		and inf_file.version.DriverVer.date.isoformat() == "2018-10-04T00:00:00+00:00"
		and inf_file.version.DriverVer.version == (12, 18, 8, 4)
	)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "Intel"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_153A",
		r"PCI\VEN_8086&DEV_153A&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_155A",
		r"PCI\VEN_8086&DEV_155A&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15A0",
		r"PCI\VEN_8086&DEV_15A0&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15A2",
		r"PCI\VEN_8086&DEV_15A2&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_156F",
		r"PCI\VEN_8086&DEV_156F&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15B7",
		r"PCI\VEN_8086&DEV_15B7&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15B9",
		r"PCI\VEN_8086&DEV_15B9&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15D7",
		r"PCI\VEN_8086&DEV_15D7&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15E3",
		r"PCI\VEN_8086&DEV_15E3&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15BB",
		r"PCI\VEN_8086&DEV_15BB&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15BD",
		r"PCI\VEN_8086&DEV_15BD&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15DF",
		r"PCI\VEN_8086&DEV_15DF&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15E1",
		r"PCI\VEN_8086&DEV_15E1&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_153B",
		r"PCI\VEN_8086&DEV_153B&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_1559",
		r"PCI\VEN_8086&DEV_1559&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15A1",
		r"PCI\VEN_8086&DEV_15A1&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15A3",
		r"PCI\VEN_8086&DEV_15A3&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_1570",
		r"PCI\VEN_8086&DEV_1570&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15B8",
		r"PCI\VEN_8086&DEV_15B8&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15D8",
		r"PCI\VEN_8086&DEV_15D8&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15D6",
		r"PCI\VEN_8086&DEV_15D6&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15BC",
		r"PCI\VEN_8086&DEV_15BC&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15BE",
		r"PCI\VEN_8086&DEV_15BE&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15E0",
		r"PCI\VEN_8086&DEV_15E0&SUBSYS_00008086",
		r"PCI\VEN_8086&DEV_15E2",
		r"PCI\VEN_8086&DEV_15E2&SUBSYS_00008086",
	]


def test_AdlerLakePCH() -> None:
	filepath = DATA_PATH / "AlderLakePCH-NDmaSecExtension.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert (
		inf_file.version
		and inf_file.version.Class == "Extension"
		and inf_file.version.DriverVer.date.isoformat() == "1968-07-18T00:00:00+00:00"
		and inf_file.version.DriverVer.version == (10, 1, 50, 8)
	)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "INTEL"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_5480",
		r"PCI\VEN_8086&DEV_5481",
		r"PCI\VEN_8086&DEV_5482",
		r"PCI\VEN_8086&DEV_5483",
		r"PCI\VEN_8086&DEV_5484",
		r"PCI\VEN_8086&DEV_5485",
		r"PCI\VEN_8086&DEV_5486",
		r"PCI\VEN_8086&DEV_5487",
		r"PCI\VEN_8086&DEV_5488",
		r"PCI\VEN_8086&DEV_5489",
		r"PCI\VEN_8086&DEV_548A",
		r"PCI\VEN_8086&DEV_548B",
		r"PCI\VEN_8086&DEV_548C",
		r"PCI\VEN_8086&DEV_548D",
		r"PCI\VEN_8086&DEV_548E",
		r"PCI\VEN_8086&DEV_548F",
		r"PCI\VEN_8086&DEV_5490",
		r"PCI\VEN_8086&DEV_5491",
		r"PCI\VEN_8086&DEV_5492",
		r"PCI\VEN_8086&DEV_5493",
		r"PCI\VEN_8086&DEV_5494",
		r"PCI\VEN_8086&DEV_5495",
		r"PCI\VEN_8086&DEV_5496",
		r"PCI\VEN_8086&DEV_5497",
		r"PCI\VEN_8086&DEV_5498",
		r"PCI\VEN_8086&DEV_5499",
		r"PCI\VEN_8086&DEV_549A",
		r"PCI\VEN_8086&DEV_549B",
		r"PCI\VEN_8086&DEV_549C",
		r"PCI\VEN_8086&DEV_549D",
		r"PCI\VEN_8086&DEV_549E",
		r"PCI\VEN_8086&DEV_549F",
		r"PCI\VEN_8086&DEV_54B0",
		r"PCI\VEN_8086&DEV_54B1",
		r"PCI\VEN_8086&DEV_54B2",
		r"PCI\VEN_8086&DEV_54B3",
		r"PCI\VEN_8086&DEV_54B4",
		r"PCI\VEN_8086&DEV_54B5",
		r"PCI\VEN_8086&DEV_54B6",
		r"PCI\VEN_8086&DEV_54B7",
		r"PCI\VEN_8086&DEV_54B8",
		r"PCI\VEN_8086&DEV_54B9",
		r"PCI\VEN_8086&DEV_54BA",
		r"PCI\VEN_8086&DEV_54BB",
		r"PCI\VEN_8086&DEV_54BC",
		r"PCI\VEN_8086&DEV_54BD",
		r"PCI\VEN_8086&DEV_54BE",
		r"PCI\VEN_8086&DEV_54BF",
	]

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X86))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_5480",
		r"PCI\VEN_8086&DEV_5481",
		r"PCI\VEN_8086&DEV_5482",
		r"PCI\VEN_8086&DEV_5483",
		r"PCI\VEN_8086&DEV_5484",
		r"PCI\VEN_8086&DEV_5485",
		r"PCI\VEN_8086&DEV_5486",
		r"PCI\VEN_8086&DEV_5487",
		r"PCI\VEN_8086&DEV_5488",
		r"PCI\VEN_8086&DEV_5489",
		r"PCI\VEN_8086&DEV_548A",
		r"PCI\VEN_8086&DEV_548B",
		r"PCI\VEN_8086&DEV_548C",
		r"PCI\VEN_8086&DEV_548D",
		r"PCI\VEN_8086&DEV_548E",
		r"PCI\VEN_8086&DEV_548F",
		r"PCI\VEN_8086&DEV_5490",
		r"PCI\VEN_8086&DEV_5491",
		r"PCI\VEN_8086&DEV_5492",
		r"PCI\VEN_8086&DEV_5493",
		r"PCI\VEN_8086&DEV_5494",
		r"PCI\VEN_8086&DEV_5495",
		r"PCI\VEN_8086&DEV_5496",
		r"PCI\VEN_8086&DEV_5497",
		r"PCI\VEN_8086&DEV_5498",
		r"PCI\VEN_8086&DEV_5499",
		r"PCI\VEN_8086&DEV_549A",
		r"PCI\VEN_8086&DEV_549B",
		r"PCI\VEN_8086&DEV_549C",
		r"PCI\VEN_8086&DEV_549D",
		r"PCI\VEN_8086&DEV_549E",
		r"PCI\VEN_8086&DEV_549F",
		r"PCI\VEN_8086&DEV_54B0",
		r"PCI\VEN_8086&DEV_54B1",
		r"PCI\VEN_8086&DEV_54B2",
		r"PCI\VEN_8086&DEV_54B3",
		r"PCI\VEN_8086&DEV_54B4",
		r"PCI\VEN_8086&DEV_54B5",
		r"PCI\VEN_8086&DEV_54B6",
		r"PCI\VEN_8086&DEV_54B7",
		r"PCI\VEN_8086&DEV_54B8",
		r"PCI\VEN_8086&DEV_54B9",
		r"PCI\VEN_8086&DEV_54BA",
		r"PCI\VEN_8086&DEV_54BB",
		r"PCI\VEN_8086&DEV_54BC",
		r"PCI\VEN_8086&DEV_54BD",
		r"PCI\VEN_8086&DEV_54BE",
		r"PCI\VEN_8086&DEV_54BF",
	]


def reg_out(reg_file: Path) -> None:
	filepath = DATA_PATH / "vioscsi_amd64.inf"
	inf_file = INFFile(filepath)
	target_os_version = INFTargetOSVersion(Architecture=Architecture.X64)
	reg = inf_file.get_driver_database_reg(target_os_version) + inf_file.get_services_reg(target_os_version)
	reg_file.write_text(
		"Windows Registry Editor Version 5.00\r\n\r\n" + reg,
		encoding="utf-16",
	)


# reg_out(Path("/tmp/test.reg"))


def test_vmnext3() -> None:
	filepath = DATA_PATH / "vmnext3.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Net" and inf_file.version.DriverVer.version == (1, 9, 11, 0)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_15AD&DEV_07B0",
	]


def test_IntelACM() -> None:
	filepath = DATA_PATH / "IntelACM_ADL_PW_1.18.11.0.INF"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "System" and inf_file.version.DriverVer.version == (1, 18, 11, 0)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "INTEL"


def test_iaAHCIC() -> None:
	filepath = DATA_PATH / "iaAHCIC.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "HDC" and inf_file.version.DriverVer.version == (18, 36, 1, 1016)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "Intel Corporation"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_A282&CC_0106",
		r"PCI\VEN_8086&DEV_34D3&CC_0106",
		r"PCI\VEN_8086&DEV_02D3&CC_0106",
		r"PCI\VEN_8086&DEV_06D2&CC_0106",
		r"PCI\VEN_8086&DEV_06D3&CC_0106",
		r"PCI\VEN_8086&DEV_A382&CC_0106",
		r"PCI\VEN_8086&DEV_43D2&CC_0106",
	]

	with (
		mock.patch("opsi.file.inf._inffile.current_timestamp", lambda: datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()),
		mock.patch("opsi.file.inf._inffile.calc_hash", lambda x: 12345678),
	):
		reg = inf_file.get_driver_database_reg(
			target_os_version=INFTargetOSVersion(Architecture=Architecture.X64),
			hardware_id=INFHardwareID(device_type="PCI", vendor_id="8086", device_id="A282"),
			oem_inf_name="iaAHCIC.inf",
		)

		# print(reg)
		return

		expected = (
			dedent(
				r"""
				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DeviceIds\USB\VID_0BDA&PID_4016]
				"RtDUsbAD_dell.inf"=hex:01,ff,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverInfFiles\RtDUsbAD_dell.inf]
				@=hex(7):72,00,74,00,64,00,75,00,73,00,62,00,61,00,64,00,5f,00,64,00,65,00,6c,00,6c,00,2e,00,69,00,6e,00,66,00,5f,00,61,00,6d,00,64,00,36,00,34,00,5f,00,30,00,30,00,62,00,63,00,36,00,31,00,34,00,65,00,00,00,00,00
				"Active"="rtdusbad_dell.inf_amd64_00bc614e"
				"Configurations"=hex(7):72,00,74,00,6b,00,75,00,73,00,62,00,61,00,64,00,2e,00,6e,00,74,00,00,00,00,00

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e]
				"Version"=hex:00,ff,09,00,00,00,00,00,6c,e9,36,4d,25,e3,ce,11,bf,c1,08,00,2b,e1,03,18,00,80,ed,2c,4b,8b,d8,01,1a,09,80,25,03,00,06,00,00,00,00,00,00,00,00,00
				"Provider"="Realtek Semiconductor Corp."
				"InfName"="rtdusbad_dell.inf"
				"OemPath"="opsi"
				"ImportDate"=hex:00,80,35,0c,d1,df,d6,01
				"SignerName"="Microsoft Windows Hardware Compatibility Publisher"
				"SignerScore"=dword:0d000005
				"StatusFlags"=dword:00000012
				@="RtDUsbAD_dell.inf"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt]
				"Service"="RtkUsbAD_2330"
				"ConfigScope"=dword:00000007
				"ConfigFlags"=dword:00000000

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device]
				"SetupPreferredAudioDevices"=hex:01,00,00,00
				"AssociatedFilters"="wdmaud"
				"Driver"="RtUsbA64.sys"
				"DriverInstallPath"="%13%"
				"CLSID"="{17CCA71B-ECD7-11D0-B908-00A0C9223196}"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers]
				"SubClasses"="wave"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\aux\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\midi\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\mixer\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Device\Drivers\wave\wdmaud.drv]
				"Driver"="wdmaud.drv"
				"Description"="Realtek USB Audio"

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Services]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Configurations\rtkusbad.nt\Services\RtkUsbAD_2330]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors\USB]

				[HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase\DriverPackages\rtdusbad_dell.inf_amd64_00bc614e\Descriptors\USB\VID_0BDA&PID_4016]
				"Configuration"="rtkusbad.nt"
				"Manufacturer"="Realtek"
				"Description"="Realtek USB Audio"

				"""
			)
			.lstrip()
			.replace("\n", "\r\n")
		)
		assert reg == expected


def test_LNBITS() -> None:
	filepath = DATA_PATH / "LNBITS.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "System" and inf_file.version.DriverVer.version == (5, 0, 21, 23)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "Lenovo"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"ACPI\IDEA2008",
	]


def test_ETD() -> None:
	filepath = DATA_PATH / "ETD.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Mouse" and inf_file.version.DriverVer.version == (32, 2, 3, 5)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "ELAN"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"HID\*ELAN0720&Col05",
		r"HID\VEN_ELAN&DEV_0720&Col05",
		r"HID\*ELAN0721&Col05",
		r"HID\VEN_ELAN&DEV_0721&Col05",
	]


def test_WbfUsbDriver() -> None:
	filepath = DATA_PATH / "WbfUsbDriver.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "Biometric" and inf_file.version.DriverVer.version == (3, 21, 12212, 20001)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "ELAN"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"USB\VID_04F3&PID_0C4B",
		r"USB\VID_04F3&PID_0C57",
	]


"""
def test_RaidDriverSmm() -> None:
	filepath = DATA_PATH / "RaidDriverSmm.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()
"""


def test_iigd_dch_d() -> None:
	filepath = DATA_PATH / "iigd_dch_d.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "Intel Corporation"

	assert [dev.hardware_id.to_string() if dev.hardware_id else None for dev in devs] == [
		r"PCI\VEN_8086&DEV_4905",
		r"PCI\VEN_8086&DEV_4907",
		r"PCI\VEN_8086&DEV_4908",
		r"PCI\VEN_8086&DEV_4909",
		r"PCI\VEN_8086&DEV_5690",
		r"PCI\VEN_8086&DEV_5690&SUBSYS_30268086",
		r"PCI\VEN_8086&DEV_5690&SUBSYS_27D21558",
		r"PCI\VEN_8086&DEV_5691",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_30268086",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_30288086",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_30298086",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_1A011EC9",
		r"PCI\VEN_8086&DEV_5692",
		r"PCI\VEN_8086&DEV_5692&SUBSYS_30268086",
		r"PCI\VEN_8086&DEV_5692&SUBSYS_30288086",
		r"PCI\VEN_8086&DEV_5692&SUBSYS_30298086",
		r"PCI\VEN_8086&DEV_5693",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_376717AA",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_384117AA",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_1A021EC9",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_132B1462",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_16111025",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_1F8C1043",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_384217AA",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_20221B50",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_891F103C",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_3AE317AA",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_8A2D103C",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_891D103C",
		r"PCI\VEN_8086&DEV_5694",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_616617AA",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_618817AA",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_171D1043",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_49808086",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_C872144D",
		r"PCI\VEN_8086&DEV_5696",
		r"PCI\VEN_8086&DEV_5696&SUBSYS_617717AA",
		r"PCI\VEN_8086&DEV_5696&SUBSYS_3D1617AA",
		r"PCI\VEN_8086&DEV_5697",
		r"PCI\VEN_8086&DEV_5697&SUBSYS_3D1617AA",
		r"PCI\VEN_8086&DEV_56A0",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_10208086",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_60011849",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_60101849",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_60121849",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_12511EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_15571EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_19971EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_18971EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_13341EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_13091EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_16341EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_13021EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_15131EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_15361EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_16291EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_13071EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_19991EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_18991EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_17191EF7",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_38881028",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_38881025",
		r"PCI\VEN_8086&DEV_56A1",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_10218086",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_10238086",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_B1021025",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_A1021025",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_13771EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_13131EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_13371EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_13241EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_15391EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_16791EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_15341EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_15731EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_13951EF7",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_60021849",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_3935172F",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_3934172F",
		r"PCI\VEN_8086&DEV_56A2",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_60031849",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_11311EF7",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_13941EF7",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_3964172F",
		r"PCI\VEN_8086&DEV_56A5",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_4017172F",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_00031458",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_00021458",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_80021043",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_18141EF7",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_12931EF7",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_60041849",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_60061849",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_8A4A103C",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_A1001025",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_3941172F",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_3943172F",
		r"PCI\VEN_8086&DEV_56A6",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_00071458",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_3945172F",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_4013172F",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_4019172F",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_4089172F",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_60071849",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_17161EF7",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_18341EF7",
		r"PCI\VEN_8086&DEV_4F80",
		r"PCI\VEN_8086&DEV_4F81",
		r"PCI\VEN_8086&DEV_4F82",
		r"PCI\VEN_8086&DEV_4F83",
		r"PCI\VEN_8086&DEV_4F84",
		r"PCI\VEN_8086&DEV_4F85",
		r"PCI\VEN_8086&DEV_4F86",
		r"PCI\VEN_8086&DEV_4F87",
		r"PCI\VEN_8086&DEV_4F88",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_22008086",
		r"PCI\VEN_8086&DEV_5691&SUBSYS_22018086",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_21008086",
		r"PCI\VEN_8086&DEV_5693&SUBSYS_21058086",
		r"PCI\VEN_8086&DEV_5694&SUBSYS_21008086",
		r"PCI\VEN_8086&DEV_5695",
		r"PCI\VEN_8086&DEV_5696&SUBSYS_20008086",
		r"PCI\VEN_8086&DEV_5697&SUBSYS_20008086",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_00061458",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_000D1458",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_00051458",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_000C1458",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_00041458",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_80051043",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_80011043",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_80061043",
		r"PCI\VEN_8086&DEV_56A0&SUBSYS_50101462",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_10248086",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_00091458",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_000A1458",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_000B1458",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_80081043",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_80091043",
		r"PCI\VEN_8086&DEV_56A1&SUBSYS_50111462",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_40AD1458",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_00081458",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_40AC1458",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_80031043",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_80041043",
		r"PCI\VEN_8086&DEV_56A2&SUBSYS_50121462",
		r"PCI\VEN_8086&DEV_56A3",
		r"PCI\VEN_8086&DEV_56A3&SUBSYS_11108086",
		r"PCI\VEN_8086&DEV_56A4",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_80071043",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_50301462",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_388A1025",
		r"PCI\VEN_8086&DEV_56A5&SUBSYS_10008086",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_60051849",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_19141EF7",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_188817AA",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_288817AA",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_237317AA",
		r"PCI\VEN_8086&DEV_56A6&SUBSYS_237517AA",
		r"PCI\VEN_8086&DEV_56B0",
		r"PCI\VEN_8086&DEV_56B0&SUBSYS_22FB17AA",
		r"PCI\VEN_8086&DEV_56B0&SUBSYS_230817AA",
		r"PCI\VEN_8086&DEV_56B1",
		r"PCI\VEN_8086&DEV_56B1&SUBSYS_12108086",
		r"PCI\VEN_8086&DEV_56B1&SUBSYS_12118086",
		r"PCI\VEN_8086&DEV_56B2",
		r"PCI\VEN_8086&DEV_56B2&SUBSYS_20008086",
		r"PCI\VEN_8086&DEV_56B2&SUBSYS_0C111028",
		r"PCI\VEN_8086&DEV_56B3",
		r"PCI\VEN_8086&DEV_56B3&SUBSYS_49058086",
		r"PCI\VEN_8086&DEV_56B3&SUBSYS_10108086",
		r"PCI\VEN_8086&DEV_56BA",
		r"PCI\VEN_8086&DEV_56BB",
		r"PCI\VEN_8086&DEV_56BC",
		r"PCI\VEN_8086&DEV_56BD",
		r"PCI\VEN_8086&DEV_56C0",
		r"PCI\VEN_8086&DEV_56C1",
	]


def test_HDXLVSST() -> None:
	filepath = DATA_PATH / "HDXLVSST.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "MEDIA" and inf_file.version.DriverVer.version == (6, 0, 9430, 1)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	for dev in devs:
		assert dev.manufacturer == "Realtek"


def test_VBoxSup() -> None:
	filepath = DATA_PATH / "VBoxSup.inf"
	inf_file = INFFile(filepath)
	inf_file.parse()

	assert inf_file.version and inf_file.version.Class == "System" and inf_file.version.DriverVer.version == (6, 1, 40, 4048)

	devs = inf_file.get_devices(target_os_version=INFTargetOSVersion(Architecture=Architecture.X64))
	assert not devs
