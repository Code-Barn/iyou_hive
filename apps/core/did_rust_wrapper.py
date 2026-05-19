# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import ctypes
import os
from pathlib import Path
from django.conf import settings


class DIDWrapper:
    def __init__(self, lib_path=None):
        """
        Initialize the DID wrapper.
        
        Args:
            lib_path: Path to the Rust-DID library. If None, uses settings.RUST_DID_LIB_PATH
            
        Raises:
            FileNotFoundError: If the library file doesn't exist
            Exception: If the library can't be loaded
        """
        if lib_path is None:
            lib_path = settings.RUST_DID_LIB_PATH
        
        lib_path = Path(lib_path)
        if not lib_path.exists():
            raise FileNotFoundError(f"Rust-DID library not found at {lib_path}")

        self.lib = ctypes.CDLL(str(lib_path))
        self.lib.generate_did_ffi.argtypes = [ctypes.c_char_p]
        self.lib.generate_did_ffi.restype = ctypes.c_char_p
        self.lib.verify_vc_ffi.argtypes = [ctypes.c_char_p]
        self.lib.verify_vc_ffi.restype = ctypes.c_bool
        self.lib.free_string.argtypes = [ctypes.c_void_p]

    def generate_did(self, method: str) -> str:
        result = self.lib.generate_did_ffi(method.encode())
        did = result.decode()
        self.lib.free_string(result)
        return did

    def verify_vc(self, credential: str) -> bool:
        return self.lib.verify_vc_ffi(credential.encode())


# Lazy initialization - only create wrapper when needed
_did_wrapper = None


def get_did_wrapper():
    """
    Get the DID wrapper instance, initializing it if necessary.
    
    Returns:
        DIDWrapper or None if library is not available
    """
    global _did_wrapper
    if _did_wrapper is None:
        try:
            _did_wrapper = DIDWrapper()
        except Exception:
            return None
    return _did_wrapper


# For backward compatibility, did_wrapper property
# Returns None if not initialized, uses get_did_wrapper() when accessed
class _LazyDidWrapper:
    def __getattr__(self, name):
        wrapper = get_did_wrapper()
        if wrapper is None:
            raise RuntimeError("Rust-DID library is not available. Please check RUST_DID_LIB_PATH setting.")
        return getattr(wrapper, name)


# For backward compatibility - did_wrapper is now a lazy-loading proxy
did_wrapper = _LazyDidWrapper()


def generate_user_did(user_id: str) -> str:
    wrapper = get_did_wrapper()
    if wrapper is None:
        raise RuntimeError("Rust-DID library is not available. Please check RUST_DID_LIB_PATH setting.")
    return wrapper.generate_did(f"user:{user_id}")


def verify_credential(credential: str) -> bool:
    wrapper = get_did_wrapper()
    if wrapper is None:
        return False  # Return False instead of raising for graceful fallback
    return wrapper.verify_vc(credential)