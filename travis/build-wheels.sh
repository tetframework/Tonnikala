#!/bin/bash
set -e -x

curl --silent --location https://rpm.nodesource.com/setup | bash -
yum -y install nodejs npm --enablerepo=epel

PYTHONS=$(echo /opt/python/*27*/bin /opt/python/*3[3456789]*/bin)

# Compile wheels
for PYBIN in $PYTHONS
do
    ${PYBIN}/pip install -r /io/dev-requirements.txt
    ${PYBIN}/pip wheel /io/ -w wheelhouse/
done

# Bundle external shared libraries into the wheels
for whl in wheelhouse/tonnikala*.whl
do
    auditwheel repair $whl -w /io/wheelhouse/
done


cd $HOME
mkdir -p tester
cd tester
cp -a /io/coverage* /io/tests /io/setup.cfg .
find -name \*.pyc -delete

# Install packages and test
for PYBIN in $PYTHONS
do
    ${PYBIN}/pip install tonnikala --no-index -f /io/wheelhouse
    (cd $HOME/tester; ${PYBIN}/py.test)
done
