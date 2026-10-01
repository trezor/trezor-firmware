#!/usr/bin/env bash
# Build and test with a bare JDK (17+), no Maven or Gradle: fetch the jars pom.xml names into
# .deps/, compile with the JDK's own compiler module, run the tests on the JUnit console launcher.
#
#   ./build.sh                    # unit tests
#   WARDD_SUITE_DIR=... ./build.sh  # plus the test against the real wardd
set -euo pipefail
cd "$(dirname "$0")"

DEPS=.deps
mkdir -p "$DEPS"
fetch() { # group artifact version
    local jar="$DEPS/$2-$3.jar"
    [ -s "$jar" ] || curl -sSfL -o "$jar" "https://repo1.maven.org/maven2/${1//.//}/$2/$3/$2-$3.jar"
}
fetch com.fasterxml.jackson.core jackson-databind 2.18.2
fetch com.fasterxml.jackson.core jackson-core 2.18.2
fetch com.fasterxml.jackson.core jackson-annotations 2.18.2
fetch com.google.protobuf protobuf-java 3.25.5
fetch org.junit.platform junit-platform-console-standalone 1.11.4

CP=$(ls "$DEPS"/*.jar | grep -v junit | paste -sd:)
JAVAC=(java -m jdk.compiler/com.sun.tools.javac.Main -Xlint:all -Werror)
# --release 17 checks API use against Java 17 too, but needs the JDK's ct.sym, which some
# distribution builds strip; then fall back to the language level alone (mvn keeps the full check)
if "${JAVAC[@]}" --release 17 -version >/dev/null 2>&1; then
    JAVAC+=(--release 17)
else
    JAVAC+=(-source 17 -target 17 -Xlint:-options)
fi
rm -rf out
"${JAVAC[@]}" -cp "$CP" -d out/main $(find src/main/java -name '*.java')
"${JAVAC[@]}" -cp "$CP:out/main:$DEPS/junit-platform-console-standalone-1.11.4.jar" -d out/test \
    $(find src/test/java -name '*.java')
java -jar "$DEPS/junit-platform-console-standalone-1.11.4.jar" execute \
    --class-path "$CP:out/main:out/test" --scan-class-path --fail-if-no-tests --disable-banner \
    --details=tree
