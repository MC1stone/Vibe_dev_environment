#!/bin/bash

# Tool Management Script

ACTION=$1
TOOL=$2
VERSION=$3

case $ACTION in
    install)
        case $TOOL in
            quarto)
                ./tools/scripts/install_quarto.sh $VERSION
                ;;
            *)
                echo "Unknown tool: $TOOL"
                exit 1
                ;;
        esac
        ;;
    check)
        case $TOOL in
            quarto)
                if command -v quarto &> /dev/null; then
                    quarto --version
                else
                    echo "Quarto not installed"
                    exit 1
                fi
                ;;
            *)
                echo "Unknown tool: $TOOL"
                exit 1
                ;;
        esac
        ;;
    list)
        echo "Available tools:"
        echo "- quarto"
        ;;
    *)
        echo "Usage: $0 [install|check|list] [tool] [version]"
        exit 1
        ;;
esac
