import ctypes
import os
from pathlib import Path
from django.conf import settings


class DIDWrapper:
    def __init__(self):
        lib_path = settings.RUST_DID_LIB_PATH
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


did_wrapper = DIDWrapper()


def generate_user_did(user_id: str) -> str:
    return did_wrapper.generate_did(f"user:{user_id}")


def verify_credential(credential: str) -> bool:
    return did_wrapper.verify_vc(credential)