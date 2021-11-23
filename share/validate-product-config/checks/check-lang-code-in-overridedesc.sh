#!/bin/bash

# make sure each language code appears only once within a given product's
# description texts (desc)

file=$1

overridedescs=$($starlet sel -t -v "count(//docset/overridedesc)" $file)
for overridedesc in $(seq 1 "$overridedescs"); do
  langcodes=$($starlet sel -t -v '(//docset/overridedesc)['"$overridedesc"']/desc/@lang' $file | sort)
  uniquelangcodes=$(echo -e "$langcodes" | sort -u)
  [[ ! "$langcodes" == "$uniquelangcodes" ]] && \
  echo -e \
    "Some overridedesc elements contain desc elements with non-unique lang attributes. Check for occurrences of the following duplicated lang attribute(s) in desc elements: "$(comm -2 -3 <(echo -e "$langcodes") <(echo -e "$uniquelangcodes") | tr '\n' ' ')"\n---"
done

exit 0
