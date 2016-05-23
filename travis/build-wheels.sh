#!/bin/bash
set -e -x

# Install a system package required by our library
yum install -y atlas-devel

# Compile wheels
for PYBIN in /opt/python/*27*/bin/ /opt/python/*3[3456789]*/bin/; do
    ${PYBIN}/pip install -r /io/dev-requirements.txt
    ${PYBIN}/pip wheel /io/ -w wheelhouse/
done

# Bundle external shared libraries into the wheels
for whl in wheelhouse/*.whl; do
    auditwheel repair $whl -w /io/wheelhouse/
done

# Install packages and test
for PYBIN in /opt/python/*27*/bin/ /opt/python/*3[3456789]*/bin/; do
    ${PYBIN}/pip install tonnikala --no-index -f /io/wheelhouse
    (cd $HOME; ${PYBIN}/nosetests tonnikala)
done

