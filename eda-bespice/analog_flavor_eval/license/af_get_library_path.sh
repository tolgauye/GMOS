#!/bin/sh

script_path=`dirname "$0"`
script_path=`cd "${script_path}"; pwd`

os=`uname -s`
version=`uname -r`
machine=`uname -m`
proc=`uname -p`

path=""

case "$os" in
    [Ll][Ii]*[Uu][Xx]*)
        case "$machine" in
            x86_64)
                path=${script_path}/../platform/linux/64/
                ;;
            i*86)
                path=${script_path}/../platform/linux/32/
                ;;
            arm*)
                path=${script_path}/../platform/linux/32/
                ;;
            aarch64)
                path=${script_path}/../platform/linux/64/
                ;;
        esac
        ;;
    [Dd]arwin*)
        case "$machine" in
            x86_64)
                path=${script_path}/../platform/osx/64/
                echo "$path\c"
                exit 0
                ;;
        esac
        ;;
    *)
        path=""
        ;;
esac

echo -n "$path"
