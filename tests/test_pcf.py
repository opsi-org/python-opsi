# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
test_pcf
"""

import os

from OPSI.Util.File.Opsi import PackageControlFile

OLD_PCF_FILENAME = "tests/test_data/control"
OLD_PCF_FILENAME_OUT = "tests/test_data/out-control"
YML_PCF_FILENAME = "tests/test_data/control.yml"
YML_PCF_FILENAME_OUT = "tests/test_data/out-control.yml"

def test_pcf_old():
	pcf = PackageControlFile(OLD_PCF_FILENAME)
	pcf.parse()
	pcf.setFilename(OLD_PCF_FILENAME_OUT)
	pcf.generate()

	assert os.path.exists(OLD_PCF_FILENAME_OUT)

	pcf_out = PackageControlFile(OLD_PCF_FILENAME_OUT)
	prod = pcf.getProduct()
	prod_out = pcf_out.getProduct()
	assert prod.getId() == prod_out.getId()
	assert prod.getProductVersion() == prod_out.getProductVersion()
	assert prod.getPackageVersion() == prod_out.getPackageVersion()
	assert prod.getName() == prod_out.getName()
	assert prod.getLicenseRequired() == prod_out.getLicenseRequired()
	assert prod.getSetupScript() == prod_out.getSetupScript()
	assert prod.getUninstallScript() == prod_out.getUninstallScript()
	assert prod.getUpdateScript() == prod_out.getUpdateScript()
	assert prod.getAlwaysScript() == prod_out.getAlwaysScript()
	assert prod.getOnceScript() == prod_out.getOnceScript()
	assert prod.getCustomScript() == prod_out.getCustomScript()
	assert prod.getUserLoginScript() == prod_out.getUserLoginScript()
	assert prod.getPriority() == prod_out.getPriority()
	assert prod.getDescription() == prod_out.getDescription()
	assert prod.getAdvice() == prod_out.getAdvice()
	assert prod.getChangelog().strip() == prod_out.getChangelog().strip()
	assert prod.getProductClassIds() == prod_out.getProductClassIds()
	assert prod.getWindowsSoftwareIds() == prod_out.getWindowsSoftwareIds()

	props = pcf.getProductProperties()
	props_out = pcf_out.getProductProperties()
	for i in range(max(len(props), len(props_out))):
		assert props[i].getProductId() == props_out[i].getProductId()
		assert props[i].getProductVersion() == props_out[i].getProductVersion()
		assert props[i].getPackageVersion() == props_out[i].getPackageVersion()
		assert props[i].getPropertyId() == props_out[i].getPropertyId()
		assert props[i].getDescription() == props_out[i].getDescription()
		assert props[i].getPossibleValues() == props_out[i].getPossibleValues()
		assert props[i].getDefaultValues() == props_out[i].getDefaultValues()
		assert props[i].getEditable() == props_out[i].getEditable()
		assert props[i].getMultiValue() == props_out[i].getMultiValue()

	deps = pcf.getProductDependencies()
	deps_out = pcf_out.getProductDependencies()
	for i in range(max(len(deps), len(deps_out))):
		assert deps[i].getProductId() == deps_out[i].getProductId()
		assert deps[i].getProductVersion() == deps_out[i].getProductVersion()
		assert deps[i].getPackageVersion() == deps_out[i].getPackageVersion()
		assert deps[i].getProductAction() == deps_out[i].getProductAction()
		assert deps[i].getRequiredProductId() == deps_out[i].getRequiredProductId()
		assert deps[i].getRequiredProductVersion() == deps_out[i].getRequiredProductVersion()
		assert deps[i].getRequiredPackageVersion() == deps_out[i].getRequiredPackageVersion()
		assert deps[i].getRequiredAction() == deps_out[i].getRequiredAction()
		assert deps[i].getRequiredInstallationStatus() == deps_out[i].getRequiredInstallationStatus()
		assert deps[i].getRequirementType() == deps_out[i].getRequirementType()

def test_pcf_controltoyml():
	pcf = PackageControlFile(OLD_PCF_FILENAME)
	pcf.parse()
	pcf.setFilename(YML_PCF_FILENAME_OUT)
	pcf.generate()

	assert os.path.exists(YML_PCF_FILENAME_OUT)

	pcf_out = PackageControlFile(YML_PCF_FILENAME_OUT)
	prod = pcf.getProduct()
	prod_out = pcf_out.getProduct()
	assert prod.getId() == prod_out.getId()
	assert prod.getProductVersion() == prod_out.getProductVersion()
	assert prod.getPackageVersion() == prod_out.getPackageVersion()
	assert prod.getName() == prod_out.getName()
	assert prod.getLicenseRequired() == prod_out.getLicenseRequired()
	assert prod.getSetupScript() == prod_out.getSetupScript()
	assert prod.getUninstallScript() == prod_out.getUninstallScript()
	assert prod.getUpdateScript() == prod_out.getUpdateScript()
	assert prod.getAlwaysScript() == prod_out.getAlwaysScript()
	assert prod.getOnceScript() == prod_out.getOnceScript()
	assert prod.getCustomScript() == prod_out.getCustomScript()
	assert prod.getUserLoginScript() == prod_out.getUserLoginScript()
	assert prod.getPriority() == prod_out.getPriority()
	assert prod.getDescription() == prod_out.getDescription()
	assert prod.getAdvice() == prod_out.getAdvice()
	assert prod.getChangelog().strip() == prod_out.getChangelog().strip()
	assert prod.getProductClassIds() == prod_out.getProductClassIds()
	assert prod.getWindowsSoftwareIds() == prod_out.getWindowsSoftwareIds()

	props = pcf.getProductProperties()
	props_out = pcf_out.getProductProperties()
	for i in range(max(len(props), len(props_out))):
		assert props[i].getProductId() == props_out[i].getProductId()
		assert props[i].getProductVersion() == props_out[i].getProductVersion()
		assert props[i].getPackageVersion() == props_out[i].getPackageVersion()
		assert props[i].getPropertyId() == props_out[i].getPropertyId()
		assert props[i].getDescription() == props_out[i].getDescription()
		assert props[i].getPossibleValues() == props_out[i].getPossibleValues()
		assert props[i].getDefaultValues() == props_out[i].getDefaultValues()
		assert props[i].getEditable() == props_out[i].getEditable()
		assert props[i].getMultiValue() == props_out[i].getMultiValue()

	deps = pcf.getProductDependencies()
	deps_out = pcf_out.getProductDependencies()
	for i in range(max(len(deps), len(deps_out))):
		assert deps[i].getProductId() == deps_out[i].getProductId()
		assert deps[i].getProductVersion() == deps_out[i].getProductVersion()
		assert deps[i].getPackageVersion() == deps_out[i].getPackageVersion()
		assert deps[i].getProductAction() == deps_out[i].getProductAction()
		assert deps[i].getRequiredProductId() == deps_out[i].getRequiredProductId()
		assert deps[i].getRequiredProductVersion() == deps_out[i].getRequiredProductVersion()
		assert deps[i].getRequiredPackageVersion() == deps_out[i].getRequiredPackageVersion()
		assert deps[i].getRequiredAction() == deps_out[i].getRequiredAction()
		assert deps[i].getRequiredInstallationStatus() == deps_out[i].getRequiredInstallationStatus()
		assert deps[i].getRequirementType() == deps_out[i].getRequirementType()


def test_pcf_yml():
	pcf = PackageControlFile(YML_PCF_FILENAME)
	pcf.parse()
	pcf.setFilename(YML_PCF_FILENAME_OUT)
	pcf.generate()

	assert os.path.exists(YML_PCF_FILENAME_OUT)

	pcf_out = PackageControlFile(YML_PCF_FILENAME_OUT)
	prod = pcf.getProduct()
	prod_out = pcf_out.getProduct()
	assert prod.getId() == prod_out.getId()
	assert prod.getProductVersion() == prod_out.getProductVersion()
	assert prod.getPackageVersion() == prod_out.getPackageVersion()
	assert prod.getName() == prod_out.getName()
	assert prod.getLicenseRequired() == prod_out.getLicenseRequired()
	assert prod.getSetupScript() == prod_out.getSetupScript()
	assert prod.getUninstallScript() == prod_out.getUninstallScript()
	assert prod.getUpdateScript() == prod_out.getUpdateScript()
	assert prod.getAlwaysScript() == prod_out.getAlwaysScript()
	assert prod.getOnceScript() == prod_out.getOnceScript()
	assert prod.getCustomScript() == prod_out.getCustomScript()
	assert prod.getUserLoginScript() == prod_out.getUserLoginScript()
	assert prod.getPriority() == prod_out.getPriority()
	assert prod.getDescription() == prod_out.getDescription()
	assert prod.getAdvice() == prod_out.getAdvice()
	assert prod.getChangelog().strip() == prod_out.getChangelog().strip()
	assert prod.getProductClassIds() == prod_out.getProductClassIds()
	assert prod.getWindowsSoftwareIds() == prod_out.getWindowsSoftwareIds()

	props = pcf.getProductProperties()
	props_out = pcf_out.getProductProperties()
	for i in range(max(len(props), len(props_out))):
		assert props[i].getProductId() == props_out[i].getProductId()
		assert props[i].getProductVersion() == props_out[i].getProductVersion()
		assert props[i].getPackageVersion() == props_out[i].getPackageVersion()
		assert props[i].getPropertyId() == props_out[i].getPropertyId()
		assert props[i].getDescription() == props_out[i].getDescription()
		assert props[i].getPossibleValues() == props_out[i].getPossibleValues()
		assert props[i].getDefaultValues() == props_out[i].getDefaultValues()
		assert props[i].getEditable() == props_out[i].getEditable()
		assert props[i].getMultiValue() == props_out[i].getMultiValue()

	deps = pcf.getProductDependencies()
	deps_out = pcf_out.getProductDependencies()
	for i in range(max(len(deps), len(deps_out))):
		assert deps[i].getProductId() == deps_out[i].getProductId()
		assert deps[i].getProductVersion() == deps_out[i].getProductVersion()
		assert deps[i].getPackageVersion() == deps_out[i].getPackageVersion()
		assert deps[i].getProductAction() == deps_out[i].getProductAction()
		assert deps[i].getRequiredProductId() == deps_out[i].getRequiredProductId()
		assert deps[i].getRequiredProductVersion() == deps_out[i].getRequiredProductVersion()
		assert deps[i].getRequiredPackageVersion() == deps_out[i].getRequiredPackageVersion()
		assert deps[i].getRequiredAction() == deps_out[i].getRequiredAction()
		assert deps[i].getRequiredInstallationStatus() == deps_out[i].getRequiredInstallationStatus()
		assert deps[i].getRequirementType() == deps_out[i].getRequirementType()
