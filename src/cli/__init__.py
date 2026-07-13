"""Aegis CLI package.

The CLI implementation lives in :mod:`src.cli.main`. The console-script entry
point and the ``python -m`` launchers import ``main`` directly from that module
(``src.cli.main:main``) rather than re-exporting it here, so that the dotted
path ``src.cli.main`` unambiguously resolves to the module on every supported
Python version. A re-exported ``main`` attribute would shadow the submodule for
attribute-based lookups such as ``unittest.mock.patch("src.cli.main.<name>")``
on Python 3.10.
"""
