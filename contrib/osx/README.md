Building macOS binaries
=======================

✗ _This script does not produce reproducible output (yet!).
   Please help us remedy this.
   [(see #7266)](https://github.com/spesmilo/electrum/issues/7266)_

This guide explains how to build Electrum binaries for macOS systems.


## Building the binary

This needs to be done on a system running macOS or OS X.

Notes about compatibility with different macOS versions:
- In general the binary is not guaranteed to run on an older version of macOS
  than what the build machine has. This is due to bundling the compiled Python into
  the [PyInstaller binary](https://github.com/pyinstaller/pyinstaller/issues/1191).
- The [bundled version of Qt](https://github.com/spesmilo/electrum/issues/3685) also
  imposes a minimum supported macOS version.
- If you want to build binaries that conform to the macOS "Gatekeeper", so as to
  minimise the warnings users get, the binaries need to be codesigned with a
  certificate issued by Apple, and starting with macOS 10.15 the binaries also
  need to be notarized by Apple's central server. The catch is that to be able to build
  binaries that Apple will notarise (due to the requirements on the binaries themselves,
  e.g. hardened runtime) the build machine needs at least macOS 10.14.
  See [#6128](https://github.com/spesmilo/electrum/issues/6128).

We currently build the release binaries on macOS 10.14.6, and these seem to run on
10.13 or newer.

Before starting, make sure that the Xcode command line tools are installed (e.g. you have `git`).

#### Build Electrum

    cd electrum
    ./contrib/osx/make_osx

This creates both a folder named Electrum.app and the .dmg file.

If you want the binaries codesigned for MacOS and notarised by Apple's central server,
provide these env vars to the `make_osx` script:

    CODESIGN_CERT="Developer ID Application: Electrum Technologies GmbH (L6P37P7P56)" \
    APPLE_ID_USER="me@email.com" \
    APPLE_ID_PASSWORD="1234" \
    ./contrib/osx/make_osx
