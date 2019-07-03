#!/bin/bash

# make sure each document format appears only once within a given link's
# language element

file=$1

links=$($starlet sel -t -v "count(//language[parent::link/parent::extralinks])" $file)
for link in $(seq 1 "$links"); do
  current_id=$($starlet sel -t -v '(//language[parent::link/parent::extralinks])['"$link"']/url[1]/@href' $file | sort)
  formats=$($starlet sel -t -v '(//language[parent::link/parent::extralinks])['"$link"']/url/@format' $file | sort)
  uniqueformats=$(echo -e "$formats" | sort -u)
  [[ ! "$formats" == "$uniqueformats" ]] && \
  echo -e \
    "For the link with the URL \"$current_id\", some of the values of format attributes in url elements are duplicated. Check for occurrences of the following duplicated format attribute(s) in the link \"$current_id\": "$(comm -2 -3 <(echo -e "$formats") <(echo -e "$uniqueformats") | tr '\n' ' ')".\n---"
done

exit 0
