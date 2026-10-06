#!/bin/bash

set -euo pipefail

this_dir="$(cd "$(dirname "$0")" && pwd)"
art_dir="${this_dir}/art"
config_json="${art_dir}/config.json"

magick_args() {
    local -n args="$1"
    local name="$2"

    local config file resize color_convert magick_args
    config="$(jq -c '.images[] | select(.name == "'"${name}"'") | {name,file,resize,color_convert,magick_args}' "${config_json}")"
    file="$(         jq -r '.file                  '  <<<"$config")"
    resize="$(       jq -r '.resize        // false'  <<<"$config")"
    color_convert="$(jq -r '.color_convert // "none"' <<<"$config")"
    magick_args="$(  jq -r '.magick_args   // "-"'    <<<"$config")"

    local src_file="${art_dir}/${file}"
    args=("${src_file}")

    local IMG_SIZE="68x140"
    case "$resize" in
        proportional) # Image is expected to be proportional to 68x140
            local size_modulus
            size_modulus=$(file "${src_file}" | perl -p -e 's/.*?\s(\d+)\sx\s(\d+).*/($1\*140)%($2*68)/g' | bc)

            if [[ "$size_modulus" != "0" ]]; then
                local size
                size=$(file "${src_file}" | perl -p -e 's/.*?\s(\d+\sx\s\d+).*/$1/g')
                >&2 cat <<EOF
ERROR: Image size (${size}) not proportional to 68x140.
Use either "ignoreAspectRatio", or "fill" resize strategy instead.
EOF
                exit 1
            fi

            args+=("-resize" "${IMG_SIZE}")
            ;;
        ignoreAspectRatio) # Image will be distorted
            args+=("-resize" "${IMG_SIZE}!")
            ;;
        fill) # Resize the image based on the smallest fitting dimension 
            args+=("-resize" "${IMG_SIZE}^" "-gravity" "center" "-extent" "${IMG_SIZE}")
            ;;
        *)
            local size
            size="$(file "${src_file}" | perl -p -e 's/.*?\s(\d+\sx\s\d+).*/$1/g')"
            if [[ "$size" != "68 x 140" ]]; then
                >&2 cat <<EOF
ERROR: Invalid image size ($size) for $file. Use "resize" to set a resize strategy.
Available resize strategies: "proportional", "ignoreAspectRatio", "fill".
EOF
                exit 1
            fi
            ;;
    esac

    case "$color_convert" in
        "monochrome") args+=("-monochrome") ;;
        "threshold")  args+=("-threshold" "50%") ;;
        "h4x4a")      args+=("-colorspace" "Gray" "-ordered-dither" "h4x4a") ;;
        "none")       ;;
        *) >&2 echo "ERROR: Unsupported color_convert option \"${color_convert}\"" && exit 1;;
    esac

    if [[ "$magick_args" != "-" ]]; then
        args+=("$magick_args")
    fi
}

gen_preview() {
    local name="$1"
    local file="${art_dir}/preview/${name}.png"
    mkdir -p "$(dirname "${file}")"
    local -a margs
    magick_args margs "$1"
    magick "${margs[@]}" "${file}"
    echo "Generated preview: ${file}"
}

gen_hex_c() {
    local name="$1"
    local -a margs
    magick_args margs "$1"
    # Skip 10 bytes (header), write as C code
    magick "${margs[@]}" "-rotate" "90" PBM:- \
        | hexdump -s 10 -v -e '"        " 18/1 "0x%02x, " "\n"' \
        | sed -e 's/0x  /0xff/g'
}

find_nice_view_widget_file() {
    local name="$1"
    local file
    file="$(find zmk -type f -name "$name" | grep nice_view | grep widgets | xargs -n 1 realpath)"
    if [[ ! -r "$file" ]]; then
        >&2 echo "ERROR: could not find $name for nice_view widget"
        exit 1
    fi
    echo "$file"
}

generate_lvgl_img() {
    local name="$1"
    cat <<EOF
#ifndef LV_ATTRIBUTE_IMG_${name^^}
#define LV_ATTRIBUTE_IMG_${name^^}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_${name^^} uint8_t ${name}_map[] = {
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif
EOF
    gen_hex_c "${name}"
    cat <<EOF
};

const lv_img_dsc_t ${name} = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 140,
  .header.h = 68,
  .data_size = 1232,
  .data = ${name}_map,
};
EOF
}

patch_art_c() {
    local images="$1"
    local art_c
    art_c="$(find_nice_view_widget_file 'art.c')"
    cat > "${art_c}" <<EOF
#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

EOF
    for name in ${images}; do
        generate_lvgl_img "${name}" >> "${art_c}"
    done
}

patch_peripheral_status_c() {
    if [[ "$#" -lt 1 || "$#" -gt 2 ]]; then
        >&2 echo "ERROR: Either one or two images must be included in the display"
        exit 1
    fi

    local img0 img1
    img0="$1"
    img1="${2:-"$1"}"

    peripheral_status_c="$(find_nice_view_widget_file 'peripheral_status.c')"
    restore_git_file "${peripheral_status_c}"
    perl -pi -e "s/balloon/$img0/g" "${peripheral_status_c}"
    perl -pi -e "s/mountain/$img1/g" "${peripheral_status_c}"
}

restore_git_file() {
    local file="$1"
    git -C "$(dirname "${file}")" \
        checkout HEAD -- "$(basename "${file}")" \
        > /dev/null
}

patch_zmk() {
    local images
    images="$(jq -r '.display[]' "${config_json}" | xargs echo)"
    patch_art_c $images
    patch_peripheral_status_c $images
    echo "ZMK nice_view widget patched with selected images: $images"
}

# # Preview all images, which is useful when testing stuff
# jq -r '.images[].name' "${config_json}" \
#     | while read -r name ; do
#     gen_preview "$name"
# done
# exit 0

patch_zmk

