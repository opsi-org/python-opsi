# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.opsipackage._associated_files import create_package_content_file, create_package_md5_file, create_package_zsync_file
from opsi.opsipackage._control_file_handling import create_product_dependencies
from opsi.opsipackage._package import OpsiPackage, PackageDependency, package_data_from_archive
from opsi.opsipackage._repo_meta import (
	RepoMetaMetadataFileType,
	RepoMetaPackage,
	RepoMetaPackageCollection,
	RepoMetaPackageCompatibility,
	RepoMetaPackageDependency,
	RepoMetaProductDependency,
	RepoMetaRepository,
)

__all__ = [
	"OpsiPackage",
	"PackageDependency",
	"package_data_from_archive",
	"create_package_content_file",
	"create_package_md5_file",
	"create_package_zsync_file",
	"create_product_dependencies",
	"RepoMetaMetadataFileType",
	"RepoMetaPackage",
	"RepoMetaPackageCollection",
	"RepoMetaPackageCompatibility",
	"RepoMetaPackageDependency",
	"RepoMetaProductDependency",
	"RepoMetaRepository",
]
