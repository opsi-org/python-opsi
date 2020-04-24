#!/bin/bash

repo_name="uibpypi"
repo_url="http://pypi.uib.gmbh:8080"
repo_username="upload"
pkg_name="python-opsi"
pkg_version=$(grep "^version = " pyproject.toml | cut -d '"' -f2)

echo -n "password for user ${repo_username}: "
read -s repo_password
echo ""

whl_name="${pkg_name/-/_}"

poetry build

curl -u "${repo_username}:${repo_password}" --form ":action=remove_pkg" --form "name=${pkg_name}" --form "version=${pkg_version}" "${repo_url}"
if [ "$whl_name" != "$pgk_name" ]; then
	curl -u "${repo_username}:${repo_password}" --form ":action=remove_pkg" --form "name=${whl_name}" --form "version=${pkg_version}" "${repo_url}"
fi

poetry publish -r "${repo_name}" -u "${repo_username}" -p "${repo_password}"
