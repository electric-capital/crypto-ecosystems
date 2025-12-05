#!/bin/bash

NEWLINE=$'\n'

print_usage() {
    echo "crypto-ecosystems 2.0"
    echo "Taxonomy of crypto open source repositories${NEWLINE}"
    echo "USAGE:${NEWLINE}    $0 <command> [arguments...]${NEWLINE}"
    echo "SUBCOMMANDS:"
    echo "    validate                   validate the taxonomy using the migrations data"
    echo "    export <output_file>       export the taxonomy to a json file"
    echo "    test                       run unit tests"
    exit 1
}

if [ $# -eq 0 ]; then
    print_usage
fi

# Check for uv
check_uv() {
    if ! command -v uv &> /dev/null; then
        echo "Error: uv is not installed on this system."
        echo ""
        echo "To install uv, run:"
        echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "For more information, visit:"
        echo "    https://docs.astral.sh/uv/getting-started/installation/"
        echo ""
        exit 1
    fi
}

check_uv

validate() {
    uv run open-dev-data validate
}

export_taxonomy() {
    uv run open-dev-data export "${@}"
}

test() {
    uv run pytest
}

help() {
    uv run open-dev-data help
}

# Main script logic
case "$1" in
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
