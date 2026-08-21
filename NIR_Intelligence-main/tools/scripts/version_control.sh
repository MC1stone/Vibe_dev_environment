#!/bin/bash

# Version Control Script for Tools

TOOL=$1
ACTION=$2
VERSION=$3

VERSION_FILE="tools/versions/${TOOL}.txt"

case $ACTION in
    update)
        # Update current version
        sed -i "s/CURRENT_VERSION:.*/CURRENT_VERSION: $VERSION/" "$VERSION_FILE"
        echo "Updated $TOOL to version $VERSION"
        ;;
    add)
        # Add available version
        echo "$VERSION" >> "$VERSION_FILE"
        echo "Added $VERSION to available versions for $TOOL"
        ;;
    check)
        # Check current version
        grep "CURRENT_VERSION:" "$VERSION_FILE" | cut -d' ' -f2
        ;;
    *)
        echo "Usage: $0 [tool] [update|add|check] [version]"
        exit 1
        ;;
esac
