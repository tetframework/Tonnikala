#!/bin/bash
set -e -x

wget http://rpm.nodesource.com/pub/el/5/x86_64/nodejs-0.10.46-1nodesource.el5.centos.x86_64.rpm -O /tmp/nodejs.rpm --quiet
yum -y --nogpgcheck localinstall /tmp/nodejs.rpm

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
cp -a /io/coverage* /io/tests .
find -name \*.pyc -delete

# Install packages and test
for PYBIN in $PYTHONS
do
    ${PYBIN}/pip install tonnikala --no-index -f /io/wheelhouse
    (cd $HOME/tester; ${PYBIN}/py.test -rsx --tb=short)
done
