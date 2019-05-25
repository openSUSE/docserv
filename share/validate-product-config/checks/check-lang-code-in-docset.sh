#!/bin/bash

# make sure each language code appears only once within a given set

file=$1

setids=$($starlet sel -t -v "//@setid" $file | sort)

for set in $(seq 1 $(echo -e "$setids" | wc -l)); do
  langcodes=$($starlet sel -t -v "//docset["$set"]/builddocs/language/@lang" $file | sort)
  uniquelangcodes=$(echo -e "$langcodes" | sort -u)
  [[ ! "$langcodes" == "$uniquelangcodes" ]] && \
  echo -e \
    "Some language elements within a set have non-unique lang attributes. Check for occurrences of the following duplicated lang attribute(s) in docset \""$($starlet sel -t -v "//docset["$set"]/@setid" $file)"\": "$(comm -2 -3 <(echo -e "$langcodes") <(echo -e "$uniquelangcodes") | tr '\n' ' ')".\n---"
done

exit 0
