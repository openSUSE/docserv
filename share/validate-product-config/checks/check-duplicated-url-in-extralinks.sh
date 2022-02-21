#!/bin/bash

# make sure each URL appears only once within a given external links section

file=$1

externallinks_sections=$($starlet sel -t -v "count(//weblinks)" $file)
for externallinks_section in $(seq 1 "$externallinks_sections"); do
  current_id=$($starlet sel -t -v '(//weblinks)['"$externallinks_section"']/ancestor::docset/@setid' $file)
  # FIXME: The removal of http(s):// here is a bit unkosher -- especially
  # since we don't add it back at the end before displaying the result to
  # the user.
  urls=$($starlet sel -t -v '(//weblinks)['"$externallinks_section"']/descendant::url/@href' $file | sed -r 's%^https?://%%' | sort)
  uniqueurls=$(echo -e "$urls" | sort -u)
  [[ ! "$urls" == "$uniqueurls" ]] && \
  echo -e \
    "Within the external links section of docset $current_id, some URLs are duplicated. Check for occurrences of the following duplicated URL(s) within the web links of docset \"$current_id\": "$(comm -2 -3 <(echo -e "$urls") <(echo -e "$uniqueurls") | tr '\n' ' ')".\n---"
done

exit 0
