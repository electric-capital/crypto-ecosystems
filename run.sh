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
    echo "    build                      build the ce executable"
    echo "    validate                   build and validate the taxonomy using the migrations data"
    echo "    export <output_file>       export the taxonomy to a json file"
    echo "    test                       run unit tests"
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

    SYSTEM_ZIG_VERSION=$(zig version | cut -d' ' -f2)
    if [[ "$SYSTEM_ZIG_VERSION
" < "0.14.0" ]]; then
       echo "zig version $version is too old, need 0.14.0+"
       exit 1
    fi
    echo "zig $SYSTEM_ZIG_VERSION found on system"
    SYSTEM_ZIG_EXEC=$(command -v zig)
}

# Detect OS and architecture
detect_platform() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    local full_platform=""
    local supported=true

    case "$os" in
        "windows"* | "mingw"* | "msys"*)
            case "$arch" in
                "x86_64")
                    full_platform="windows-x86_64"
                    ;;
                *)
                    supported=false
                    ;;
            esac
            ;;
        "darwin"*)
            case "$arch" in
                "arm64")
                    full_platform="macos-aarch64"
                    ;;
                *)
                    supported=false
                    ;;
            esac
            ;;
        "linux"*)
            case "$arch" in
                "x86_64")
                    full_platform="linux-x86_64"
                    ;;
                *)
                    supported=false
                    ;;
            esac
            ;;
        *)
            supported=false
            ;;
    esac

    

    if [ "$supported" = false ]; then
        # If you are on an unsupported architecture, check to see if a
        # sufficient zig compiler is available.
        detect_local_zig
        if [ -z "${SYSTEM_ZIG_EXEC}" ]; then
            echo "$os-$arch is unsupported with the embedded build system."
            echo ""
            echo "Please use an architecture of the following:"
            echo "    - linux-x86_64"
            echo "    - macos-aarch64"
            echo ""
            echo "Or if you can run your own compiler do the following:"
            echo "1/ Download a zig compiler with a version > 0.14.0 here: https://ziglang.org/download/"
            echo "2/ Install zig into your path"
            echo "3/ Run ./run.sh again"
            exit 1
        fi
    fi
    PLATFORM="$full_platform"
}

detect_platform

# Build function
setup() {
    if [ -z "${SYSTEM_ZIG_EXEC:x}" ]; then
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
    $ZIG_EXEC build -Doptimize=ReleaseFast
}

validate() {
    $ZIG_EXEC build -Doptimize=ReleaseFast run -- validate
}

export_taxonomy() {
    $ZIG_EXEC build -Doptimize=ReleaseFast run -- export "${@}"
}

test() {
    $ZIG_EXEC build -Doptimize=ReleaseFast test --summary all
}

help() {
    $ZIG_EXEC build -Doptimize=ReleaseFast run -- help
}

# Main script logic
case "$1" in
    "build")
        build
        ;;
    "validate")
        validate "$@"
        ;;
    "export")
        shift
        export_taxonomy "$@"
        ;;
    "test")
        test
        ;;
    "help")
        help
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
esac
