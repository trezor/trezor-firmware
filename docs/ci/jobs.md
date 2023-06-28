# CI pipeline
(Generated automatically by `tools/generate_ci_docs.py`. Do not edit by hand.)

It consists of multiple stages below, each having one or more jobs
Latest CI pipeline of master branch can be seen at [https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines/master/latest](https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines/master/latest)

## ENVIRONMENT stage - [environment.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/environment.yml)
Connected with creating the testing image for CI.

Consists of **3 jobs** below:

### [.environment](https://github.com/trezor/trezor-firmware/blob/master/ci/environment.yml#L7)
Environment job builds the `ci/Dockerfile` and pushes the built docker image
into our GitLab registry. Since modifications of this Dockerfile are very rare
this is a _manual_ job which needs to be triggered on GitLab.
Almost all CI jobs run inside this docker image.

### [environment manual](https://github.com/trezor/trezor-firmware/blob/master/ci/environment.yml#L31)

### [environment scheduled](https://github.com/trezor/trezor-firmware/blob/master/ci/environment.yml#L35)

---
## PREBUILD stage - [prebuild.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml)
Static checks on the code.

Consists of **6 jobs** below:

### [style prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L16)
Check the code for style correctness and perform some static code analysis.
Biggest part is the python one - using `flake8`, `isort`, `black`, `pylint` and `pyright`,
also checking Rust files by `rustfmt` and C files by `clang-format`.
Changelogs formats are checked.

### [common prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L25)
Check validity of coin definitions and protobuf files.

### [gen prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L32)
Check validity of auto-generated files.

### [editor prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L39)
Checking format of .editorconfig files.

### [release commit messages prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L46)
Checking the format of release commit messages.

### [changelog prebuild](https://github.com/trezor/trezor-firmware/blob/master/ci/prebuild.yml#L63)
Verifying that all commits changing some functionality have a changelog entry
or contain `[no changelog]` in the commit message.

---
## BUILD stage - [build.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml)
All builds are published as artifacts so they can be downloaded and used.

Consists of **31 jobs** below:

### [core fw regular build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L20)
Build of Core into firmware. Regular version.
**Are you looking for Trezor T firmware build? This is most likely it.**

### [core fw regular debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L43)
Build of Core into firmware with enabled _debug_ mode. In debug mode you can
upload mnemonic seed, use debug link etc. which enables device tests. Storage
on the device gets wiped on every start in this firmware.

### [core fw regular production build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L58)

### [core fw btconly build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L81)
Build of Core into firmware. Bitcoin-only version.

### [core fw btconly debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L98)

### [core fw btconly production build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L121)

### [core fw DISC1 build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L140)

### [core fw R debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L159)

### [core fw R build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L177)

### [core unix regular build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L196)
Non-frozen emulator build. This means you still need Python files
present which get interpreted.

### [core unix regular R build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L209)
Non-frozen emulator build for model R.

### [core unix regular asan build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L223)

### [core unix frozen regular build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L244)
Build of Core into UNIX emulator. Something you can run on your laptop.
Frozen version. That means you do not need any other files to run it,
it is just a single binary file that you can execute directly.

### [core unix frozen btconly debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L263)
Build of Core into UNIX emulator. Something you can run on your laptop.
Frozen version. That means you do not need any other files to run it,
it is just a single binary file that you can execute directly.
See [Emulator](../core/emulator/index.md) for more info.
Debug mode enabled, Bitcoin-only version.

### [core unix frozen btconly debug asan build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L279)

### [core unix frozen debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L302)
Build of Core into UNIX emulator. Something you can run on your laptop.
Frozen version. That means you do not need any other files to run it,
it is just a single binary file that you can execute directly.
**Are you looking for a Trezor T emulator? This is most likely it.**

### [core unix frozen R debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L315)

### [core unix frozen R debug build arm](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L330)

### [core unix frozen debug asan build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L348)

### [core unix frozen debug build arm](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L364)

### [core macos frozen regular build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L386)

### [crypto build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L411)
Build of our cryptographic library, which is then incorporated into the other builds.

### [legacy fw regular build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L441)

### [legacy fw regular debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L457)

### [legacy fw btconly build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L474)

### [legacy fw btconly debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L493)

### [legacy emu regular debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L514)
Regular version (not only Bitcoin) of above.
**Are you looking for a Trezor One emulator? This is most likely it.**

### [legacy emu regular debug asan build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L529)

### [legacy emu regular debug build arm](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L547)

### [legacy emu btconly debug build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L573)
Build of Legacy into UNIX emulator. Use keyboard arrows to emulate button presses.
Bitcoin-only version.

### [legacy emu btconly debug asan build](https://github.com/trezor/trezor-firmware/blob/master/ci/build.yml#L590)

---
## TEST stage - [test.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml)
All the tests run test cases on the freshly built emulators from the previous `BUILD` stage.

Consists of **39 jobs** below:

### [core unit python test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L15)
Python unit tests, checking core functionality.

### [core unit python R test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L24)
Python unit tests, checking core functionality. For model R.

### [core unit rust test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L33)
Rust unit tests.

### [core unit asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L42)

### [core device test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L63)
Device tests for Core. Running device tests and also comparing screens
with the expected UI result.
See artifacts for a comprehensive report of UI.
See [docs/tests/ui-tests](../tests/ui-tests.md) for more info.

### [core device R test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L94)

### [core device asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L126)

### [core btconly device test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L145)
Device tests excluding altcoins, only for BTC.

### [core btconly device asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L165)

### [core monero test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L186)
Monero tests.

### [core monero asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L206)

### [core u2f test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L229)
Tests for U2F and HID.

### [core u2f asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L248)

### [core fido2 test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L266)
FIDO2 device tests.

### [core fido2 asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L289)

### [core click test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L309)
Click tests - UI.
See [docs/tests/click-tests](../tests/click-tests.md) for more info.

### [core click R test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L341)
Click tests.
See [docs/tests/click-tests](../tests/click-tests.md) for more info.

### [core click asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L370)

### [core upgrade test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L391)
Upgrade tests.
See [docs/tests/upgrade-tests](../tests/upgrade-tests.md) for more info.

### [core upgrade asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L410)

### [core persistence test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L432)
Persistence tests - UI.

### [core persistence asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L462)

### [core hwi test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L480)

### [crypto test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L499)

### [legacy device test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L531)
Legacy device test - UI.

### [legacy asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L559)

### [legacy btconly test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L571)

### [legacy btconly asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L591)

### [legacy upgrade test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L606)

### [legacy upgrade asan test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L625)

### [legacy hwi test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L646)

### [python test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L666)

### [python support test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L685)

### [rust test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L694)

### [storage test](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L704)

### [core unix memory profiler](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L728)

### [core firmware flash size checker](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L754)
Finds out how much flash space we have left in the firmware build
Fails if the free space is less than certain threshold

### [core firmware flash size compare master](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L767)
Compares the current flash space with the situation in the current master
Fails if the new binary is significantly larger than the master one
(the threshold is defined in the script, currently 5kb).
Allowing fir failure, not to prevent the merge.
Also generates a report with the current situation

### [connect test core](https://github.com/trezor/trezor-firmware/blob/master/ci/test.yml#L782)

---
## TEST-NONENGLISH stage - [test-nonenglish.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml)
Tests for non-english languages, that run only nightly
- apart from that, they run also for every branch containing "translations" in its name

Consists of **16 jobs** below:

### [core device test czech](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L14)
START_DEVICE_TESTS

### [core device test french](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L50)

### [core device test german](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L86)

### [core device test spanish](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L122)

### [core device R test czech](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L158)

### [core device R test french](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L194)

### [core device R test german](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L230)

### [core device R test spanish](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L266)

### [core click test czech](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L306)
START_CLICK_TESTS

### [core click test french](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L341)

### [core click test german](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L376)

### [core click test spanish](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L411)

### [core click R test czech](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L446)

### [core click R test french](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L481)

### [core click R test german](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L516)

### [core click R test spanish](https://github.com/trezor/trezor-firmware/blob/master/ci/test-nonenglish.yml#L551)

---
## POSTTEST stage - [posttest.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/posttest.yml)

Consists of **2 jobs** below:

### [core unix coverage posttest](https://github.com/trezor/trezor-firmware/blob/master/ci/posttest.yml#L10)

### [unix ui changes](https://github.com/trezor/trezor-firmware/blob/master/ci/posttest.yml#L33)

---
## DEPLOY stage - [deploy.yml](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml)

Consists of **14 jobs** below:

### [release core fw regular deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L5)

### [release core fw btconly deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L27)

### [release core fw regular debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L49)

### [release core fw btconly debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L71)

### [release legacy fw regular deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L95)

### [release legacy fw btconly deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L117)

### [release legacy fw regular debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L139)

### [release legacy fw btconly debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L161)

### [release core unix debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L185)

### [release legacy unix debug deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L211)

### [ui tests fixtures deploy](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L239)

### [ui tests fixtures deploy nonenglish](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L264)

### [sync emulators to aws](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L304)

### [common sync](https://github.com/trezor/trezor-firmware/blob/master/ci/deploy.yml#L330)

---
