# Symbian Series 80 2.0 build tools

Linux build tools (GnuPoc, GCC 2.9), an ARM emulator kit, tips, pitfalls and performance notes for
native Symbian Series 80 2.0 (Nokia 9300 / 9500, Symbian 7.0s, EKA1) development, and the builds
of the TLS 1.2 patch (`ssladaptor.dll`).

| Where | What |
|---|---|
| `toolchain/` | The EKA1 toolchain and the SDKs on Linux: `setup_eka1_toolchain.sh` (GnuPoc + GCC 2.9 + S60 2.1 SDK), `setup_s80_sdk.sh` (the Series 80 2.0 SDK), `setup_vm_noroot.sh` (the same without root, in stages), `build_s80.sh` (build any S80 app), the patches they apply |
| `gcc-539-2aeh-source.tar.bz2` | The source of the Symbian GCC 2.9-psion-98r2 compiler |
| `native9300/` | [Native 9300 notes](native9300/README.md): GCC 2.9 pitfalls, ARM speed-ups, the data cache, building and packaging, network speeds; the ARM emulator kit (`emu/`) and reusable code (`lib/`: fastmem, JPEG, PNG, a 3D renderer) |
| `BUILD_SYMBIAN_TLS.md`, `out/`, `upstream/` | Building and installing `ssladaptor.dll` (the TLS 1.2 patch, from janseris/symbian-tls + bearssl-symbian), our builds `ssladaptor_v20-fixN*.dll`, the texts sent upstream |
| `j2me/` | Archived: J2ME on the 9300 (installing a J2ME app, why signed MIDlets don't work) |

Clone it next to the other repos it works with (all in one folder):

```
git clone https://github.com/janseris/symbian-s80-build-tools.git
git clone https://github.com/janseris/s60-sdk-2.1.git          # private: Nokia's SDK
git clone https://github.com/janseris/s80_DP_2_0_SDK.git       # private: Nokia's SDK, also a ready-made toolchain (prebuilt/)
git clone -b eka1-java-fixes https://github.com/janseris/symbian-tls.git symbian-tls
git clone -b eka1-fixes https://github.com/janseris/bearssl-symbian.git bearssl
```

The fastest start is the ready-made toolchain in `s80_DP_2_0_SDK/prebuilt/` (Ubuntu 24.04);
`toolchain/` builds the same from source. Apps built with it: Maps 9300 (`janseris/maps9300`),
MP4 Player, GnuBox for S80 (`janseris/gnubox-s80`), Net Helper.
