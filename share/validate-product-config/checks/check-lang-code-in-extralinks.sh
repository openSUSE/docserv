#!/bin/bash

# make sure each language code appears only once within a given link's
# language elements

file=$1

links=$($starlet sel -t -v "count(//link[parent::weblinks])" $file)
for link in $(seq 1 "$links"); do
  current_id=$($starlet sel -t -v '(//link[parent::weblinks])['"$link"']/language[1]/url[1]/@href' $file | sort)
  langcodes=$($starlet sel -t -v '(//link[parent::weblinks])['"$link"']/language/@lang' $file | sort)
  uniquelangcodes=$(echo -e "$langcodes" | sort -u)
  [[ ! "$langcodes" == "$uniquelangcodes" ]] && \
  echo -e \
    "Some of the localized versions of \"$current_id\" have non-unique lang attributes. Check for occurrences of the following duplicated lang attribute(s) in the language elements of web link \"$current_id\": "$(comm -2 -3 <(echo -e "$langcodes") <(echo -e "$uniquelangcodes") | tr '\n' ' ')".\n---"
done

exit 0
