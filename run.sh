#!/bin/bash

# Exit on error
set -e

ZIG_VERSION="0.14.0"
NEWLINE=$'\n'

print_usage() {
    echo "crypto-ecosystems 2.0"
    echo "Taxonomy of crypto open source repositories${NEWLINE}"
    echo "USAGE:${NEWLINE}    $0 <command> [arguments...]${NEWLINE}"
    echo "SUBCOMMANDS:"
    echo "    build                      Build the executable"
    echo "    validate                   Validate the taxonomy using migrations data"
    echo "    export <output_file>       Export taxonomy to a JSON file"
    echo "    test                       Run unit tests"
    echo "    debug                      Run in debug mode"
    exit 1
}

if [ $# -eq 0 ]; then
    print_usage
fi

detect_local_zig() {
    if ! command -v zig &> /dev/null; then
       echo "zig not found"
       exit 1
    fi

    SYSTEM_ZIG_VERSION=$(zig version)
    if [ "$(echo -e "$SYSTEM_ZIG_VERSION\n$ZIG_VERSION" | sort -V | head -n 1)" != "$ZIG_VERSION" ]; then
       echo "zig version $SYSTEM_ZIG_VERSION is too old, need 0.14.0+"
       exit 1
    fi
    echo "zig $SYSTEM_ZIG_VERSION found on system"
    SYSTEM_ZIG_EXEC=$(command -v zig)
}

detect_platform() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    local full_platform=""

    case "$os" in
        "windows"*)
            [[ "$arch" == "x86_64" ]] && full_platform="windows-x86_64" || echo "Unsupported platform: $os-$arch" && exit 1
            ;;
        "darwin"*)
            [[ "$arch" == "arm64" ]] && full_platform="macos-aarch64" || echo "Unsupported platform: $os-$arch" && exit 1
            ;;
        "linux"*)
            [[ "$arch" == "x86_64" ]] && full_platform="linux-x86_64" || echo "Unsupported platform: $os-$arch" && exit 1
            ;;
        *)
            echo "Unsupported platform: $os-$arch"
            exit 1
            ;;
    esac
    PLATFORM="$full_platform"
}

detect_platform

setup() {
    if [ -z "$SYSTEM_ZIG_EXEC" ]; then
        ZIG_FILE_ROOT="zig-${PLATFORM}-${ZIG_VERSION}"
        ZIG_PACKAGE="toolchains/${ZIG_FILE_ROOT}.tar.xz"
        mkdir -p .tcache
        if [ ! -f ".tcache/$ZIG_FILE_ROOT/zig" ]; then
            echo "Setting up build system for $PLATFORM..."
            tar -xf "${ZIG_PACKAGE}" -C .tcache
        fi
        ZIG_EXEC=".tcache/${ZIG_FILE_ROOT}/zig"
    else
        echo "Using system zig for build"
        ZIG_EXEC="${SYSTEM_ZIG_EXEC}"
    fi
}

setup
if [ ! -f "$ZIG_EXEC" ] || [ ! -x "$ZIG_EXEC" ]; then
    echo "Error: Zig executable not found or not executable at $ZIG_EXEC"
    exit 1
fi

build() {
    $ZIG_EXEC build -Doptimize=ReleaseSafe
}

validate() {
    $ZIG_EXEC build -Doptimize=ReleaseSafe run -- validate
}

export_taxonomy() {
    $ZIG_EXEC build -Doptimize=ReleaseSafe run -- export "${@}"
}

test() {
    $ZIG_EXEC build -Doptimize=ReleaseSafe test --summary all
}

debug() {
    echo "Running in Debug mode..."
    set -x
    build
    validate
    set +x
}

case "$1" in
    "build") build ;;
    "validate") validate ;;
    "export") shift; export_taxonomy "$@" ;;
    "test") test ;;
    "debug") debug ;;
    *) echo "Unknown command: $1"; exit 1 ;;
esac
