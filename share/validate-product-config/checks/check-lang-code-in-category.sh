#!/bin/bash

# make sure each language code appears only once within a given product's
# category names

file=$1

categories=$($starlet sel -t -v "count(//category)" $file)
for category in $(seq 1 "$categories"); do
  current_id=$($starlet sel -t -v '//category['"$category"']/@categoryid' $file | sort)
  langcodes=$($starlet sel -t -v '//category['"$category"']/language/@lang' $file | sort)
  uniquelangcodes=$(echo -e "$langcodes" | sort -u)
  [[ ! "$langcodes" == "$uniquelangcodes" ]] && \
  echo -e \
    "Some of the name translations of category \"$current_id\" have non-unique lang attributes. Check for occurrences of the following duplicated lang attribute(s) in the language elements of category \"$current_id\": "$(comm -2 -3 <(echo -e "$langcodes") <(echo -e "$uniquelangcodes") | tr '\n' ' ')".\n---"
done

exit 0
