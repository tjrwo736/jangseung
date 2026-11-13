"""SHA-256 without loading OpenSSL.

``import hashlib`` loads the OpenSSL module, about 4 ms on every hook call.
CPython 3.12 and later build SHA-256 in as ``_sha2``, with the same digests.
"""

try:
    from _sha2 import sha256  # CPython 3.12 and later
except ImportError:
    try:
        from _sha256 import sha256  # CPython 3.10 and 3.11
    except ImportError:  # a build without the built-in module
        from hashlib import sha256

__all__ = ["sha256"]
