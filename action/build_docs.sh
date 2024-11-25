#!/usr/bin/env bash

THEME="sphinx_rtd_theme"
OUTPUT_DIR="../sphinx_output"
REPO_DIR=$PWD

mkdir -p ../sphinx_project/source
pushd ../sphinx_project

pip install $THEME

cat <<EOL > source/conf.py
project = "README"
html_theme = "$THEME"
EOL

cp "../README.rst" ../sphinx_project/source/index.rst
sphinx-build -b html source $OUTPUT_DIR

popd
mv ../sphinx_project/$OUTPUT_DIR .
rm -rf ../sphinx_project
