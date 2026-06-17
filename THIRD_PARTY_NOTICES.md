# Third-Party Notices

Meeting Mojiokoshi uses third-party software and model files. This notice is
informational and does not replace the license texts shipped by the upstream
projects. Review the upstream licenses before distributing binary builds.

## Runtime Python Packages

The source package depends on the following runtime packages:

- `faster-whisper`: MIT
- `ctranslate2`: MIT
- `huggingface-hub`: Apache-2.0
- `hf-xet`: Apache-2.0
- `tokenizers`: Apache-2.0
- `onnxruntime`: MIT
- `av` / PyAV: BSD-3-Clause
- `numpy`: BSD-3-Clause, with bundled components such as OpenBLAS and GCC
  runtime libraries in binary wheels
- `Pillow`: MIT-CMU, with bundled image libraries in binary wheels
- `platformdirs`: MIT
- `pystray`: LGPLv3
- `python-xlib`: LGPLv2 or later, used by pystray on Linux
- `soundcard`: BSD-3-Clause
- `cffi`: MIT
- `requests`: Apache-2.0
- `filelock`: MIT
- `fsspec`: BSD-3-Clause
- `tqdm`: MPL-2.0 and MIT
- `PyYAML`: MIT
- `flatbuffers`: Apache-2.0
- `protobuf`: BSD-3-Clause

## PyInstaller Builds

PyInstaller itself is GPLv2-or-later with an exception for distributing
programs built with PyInstaller. The generated application also bundles Python
packages and native shared libraries from their wheels.

Binary builds made from the default dependency set may include shared libraries
from:

- FFmpeg / libav libraries bundled by PyAV
- x264 and x265 libraries bundled by the PyAV FFmpeg build
- OpenBLAS, libgfortran, libquadmath, and libgomp from numeric/runtime wheels
- OpenSSL, libffi, X11/XCB, ALSA, and other platform libraries depending on the
  build environment

The PyAV FFmpeg builds currently used by upstream wheels enable x264 and x265.
Those projects are GPL-licensed. Do not publish binary releases unless you have
confirmed that the resulting distribution satisfies all applicable third-party
license obligations, or rebuild the dependency stack without GPL components.

GitHub Actions intentionally does not upload binary artifacts from public CI.
Release archives should be published manually only after this review is complete.

## Whisper Model Files

The application downloads trusted Faster Whisper model repositories from
Hugging Face on first use. These model files are not bundled in this repository
or in the default release archive. The pinned model repositories used by the
application declare the MIT license:

- `Systran/faster-whisper-tiny`
- `Systran/faster-whisper-base`
- `Systran/faster-whisper-small`
- `Systran/faster-whisper-medium`

## Source Locations

See `pyproject.toml` and `requirements/constraints.txt` for the exact packages
and versions used by a given build.
