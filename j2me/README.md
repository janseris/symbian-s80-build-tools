# J2ME on the Nokia 9300 (archived)

Kept for reference: the 9300 work moved to native Symbian C++ apps, so this isn't maintained.
What's here: where the J2ME public transport app (`pubtran-j2me`) and its pieces live, how a J2ME
app gets onto the phone, and why signed MIDlets can't be used on Series 80 v2.

The Nokia 9300 / 9500 Communicator runs **Series 80 v2** on **Symbian 7.0s (EKA1)**.
It is not S60: the S60v2-era notes below apply only where stated, and patches for
Symbian 9.x (S60v3+, EKA2) don't work on it.

## Repositories

The work is split into separate repositories, cloned side by side in `phoneapk/`:

| Folder | Repository | What it is |
|---|---|---|
| `symbian-s80-build-tools/` (this repo; this page is its `j2me/`) | `janseris/symbian-s80-build-tools` | Build tools, prebuilt TLS DLLs, native-app notes |
| `.` | `janseris/Czech-Public-Transport-Symbian-App` | The Jízdní řády Android app's decompiled/patched copy and API capture, the C# client (`PubtranClient/`), `tlsprobe/` |
| `pubtran-j2me/` | `janseris/pubtran-j2me` (fork of [gtrxac/discord-j2me](https://github.com/gtrxac/discord-j2me)) | The J2ME public transport app for the phone (the first user of the TLS patch) |
| `symbian-tls/` | [janseris/symbian-tls](https://github.com/janseris/symbian-tls), branch `eka1-java-fixes` (fork of shinovon/symbian-tls) | The TLS 1.2 patch (`SSLADAPTOR.dll`) with the EKA1/Java fixes |
| `bearssl/` | [janseris/bearssl-symbian](https://github.com/janseris/bearssl-symbian), branch `eka1-fixes` | BearSSL for the patch |

Clone them into one folder:

```
git clone https://github.com/janseris/symbian-s80-build-tools.git
git clone https://github.com/janseris/pubtran-j2me.git
git clone -b eka1-java-fixes https://github.com/janseris/symbian-tls.git symbian-tls
git clone -b eka1-fixes https://github.com/janseris/bearssl-symbian.git bearssl
```

## Installing a J2ME app

1. The TLS patch first (`https://` from Java goes through it): see
   [BUILD_SYMBIAN_TLS.md](../BUILD_SYMBIAN_TLS.md#the-dlls-and-installing-them).
2. **The app** (here pubtran-j2me). In `android-to-j2me-kit/nokia9300/ota/` (the one over-the-air server for all the apps; copy `pubtran-j2me/bin/pubtran_s80.jar` + `.jad` there) run `start_ota_server.bat` (port 8000). In the phone's
   browser open `http://<PC address>:8000/` (USB networking: `http://192.168.137.1:8000/`)
   and download the **`.jar` directly**. Opening the `.jad` makes the phone reject the suite
   before it downloads the jar. The server also serves `ssladaptor.dll` / `ssladaptor_log.dll`
   and has an upload page (`/upload`) for sending logs from the phone to the PC.

## Why signed MIDlets don't work on the 9300

Unsigned MIDlets can't open `socket://` (SecurityException), so a Java TLS implementation
(BouncyCastle, as discord-j2me uses on other phones) would need a signed MIDlet. On the 9300
every signed suite was refused ("Instalace aplikace byla odmítnuta serverem jazyka Java" /
"Digitální podpis nelze ověřit"), including a 2 KB test MIDlet, with:

- the "Darkman" certificate from discord-j2me,
- an own self-signed certificate,
- an own root + signer chain,

each imported on the phone and allowed for application installation.

The reason: on Nokia phones of this generation the set of root certificates that can
verify a MIDlet signature is **closed** (fixed in ROM by Nokia, operators and the big CAs).
An imported certificate can be marked as trusted, but it never maps to a MIDP protection
domain, so a signature chaining to it can't be verified. Forum Nokia's *MIDP 2.0: Tutorial
On Signed MIDlets* says self-signed certificates work only in the emulator,
"this approach will not work in actual Nokia devices since the set of root certificates is closed".

The workarounds used on newer phones don't exist for Series 80 v2:

- The discord-j2me "Darkman"/expired-certificate trick and nnproject's
  [Java Permissions patch](http://nnproject.cc/jrtsecuritypatch) target Symbian 9.x
  (S60v3 and later; the patch needs Symbian 9.3+ and Open4All).
- [gtrxac.fi/j2me/proxyless](https://gtrxac.fi/j2me/proxyless) lists Series 80 2nd Edition
  (Symbian 7.0) as supported **only through the system-level TLS 1.2 patch**
  ("certificate is not required"), not through Java TLS.
- The nnproject [TLS 1.2 patch](http://nnproject.cc/tls) has an EKA1 build (BearSSL) for
  S60v2, S80v2, S90 and UIQ2, and applies to native and J2ME applications.

So the app uses only `https://` through `HttpConnection`, which goes through the patched
`SSLADAPTOR.dll`. The Java TLS code stays in `pubtran-j2me` behind `//#ifdef JAVA_TLS` for
emulators and other phones. No signing keys are needed.
