#!/bin/bash

set -euo pipefail

this_dir="$(cd "$(dirname "$0")" && pwd)"
firmware_dir="${this_dir}/firmware"
dev_mount="/Volumes/NICENANO"

# USB serial numbers of this keyboard's nice!nanos, as printed by
# serial_number while in the bootloader. A board that matches neither
# (someone else's urchin, a replaced controller) needs a typed confirmation.
left_serial="BBA111E40B63F809"
right_serial="D7ED1AAC6770C853"

# SPUSBDataType went away in newer macOS, which left this silently empty.
serial_number() {
    system_profiler SPUSBHostDataType 2>/dev/null \
        | sed -n '/nice!nano/,/Serial Number/p' \
        | awk -F ': ' '/Serial Number/ { print $2; exit }'
}

# Prints which half the mounted board is, from its serial or by asking.
identify() {
    local serial="$1"
    if [[ -n "$serial" && "$serial" == "$left_serial" ]]; then
        echo left
    elif [[ -n "$serial" && "$serial" == "$right_serial" ]]; then
        echo right
    else
        >&2 echo "Unknown board (serial: ${serial:-none})."
        local answer=""
        while [[ "$answer" != left && "$answer" != right ]]; do
            read -r -p "Type 'left' or 'right' to confirm which half this is: " answer < /dev/tty
        done
        echo "$answer"
    fi
}

wait_mount() {
    while [[ ! -d "$dev_mount" ]]; do
        sleep 1
    done
}

wait_gone() {
    while [[ -d "$dev_mount" ]]; do
        sleep 1
    done
    sleep 2
}

# Waits until the board in the bootloader is the requested half.
wait_reset() {
    local half="$1"
    while true; do
        echo "Plug in and double click the reset button on the $half half ..."
        wait_mount
        local serial detected
        serial="$(serial_number)"
        echo "===> SERIAL NUMBER: ${serial:-none}"
        detected="$(identify "$serial")"
        if [[ "$detected" == "$half" ]]; then
            return
        fi
        echo "That is the $detected half, not the $half half. Not flashing it."
        echo "Unplug it."
        wait_gone
    done
}

firmware() {
    local half="$1"
    file="$(find "$firmware_dir" -type f -name '*'"$half"'*.uf2' | head -n 1)"
    if [[ -z "$file" ]]; then
        >&2 echo "ERROR: Firmware for $half half not found. Have you run build.sh?"
        exit 1
    fi
    echo "$file"
}

flash() {
    local half="$1"
    local image="${2:-$half}"
    image="$(firmware "$image")"
    wait_reset "$half"
    echo "Detected $half, using image $image."
    echo "Flashing ..."
    while [[ -d "$dev_mount" ]]; do
        cp "$image" "$dev_mount" > /dev/null 2>&1 || true
    done
    echo "Flashed $half half!"
    wait_gone
}

# flash left reset
# flash right reset
flash left
flash right
