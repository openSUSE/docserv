#!/bin/bash

# make sure each dc appears only once within a language

file=$1

languages=$($starlet sel -t -v "count(//language)" $file | sort)
for language in $(seq 1 "$languages"); do
  currentlanguage=$($starlet sel -t -c "(//language)["$language"]" $file)
  langcode=$(echo -e "$currentlanguage" | $starlet sel -t -v "(//@lang)[1]" $file)
  setid=$($starlet sel -t -v "(//language)["$language"]/ancestor::docset/@setid" $file)
  dcs=$(echo -e "$currentlanguage" | $starlet sel -t -v "//dc" | sort)
  uniquedcs=$(echo -e "$dcs" | sort -u)
  [[ ! "$dcs" == "$uniquedcs" ]] && \
  echo -e \
    "Some dc elements within a language have non-unique values. Check for occurrences of the following duplicated dc elements in docset=$setid/language=$langcode: "$(comm -2 -3 <(echo -e "$dcs") <(echo -e "$uniquedcs") | tr '\n' ' ')".\n---"
done

exit 0
