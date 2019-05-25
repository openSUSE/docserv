#!/bin/bash

# make sure each subdeliverable appears only once within a dc

file=$1

deliverables=$($starlet sel -t -v "count(//deliverable)" $file | sort)
for deliverable in $(seq 1 $deliverables); do
  currentdeliverable=$($starlet sel -t -c "(//deliverable)["$deliverable"]" $file)
  [[ ! $(echo -e "$currentdeliverable" | $starlet sel -t -c "(//subdeliverable)") ]] && continue
  langcode=$($starlet sel -t -v "(//deliverable)["$deliverable"]/ancestor::language/@lang" $file)
  setid=$($starlet sel -t -v "(//deliverable)["$deliverable"]/ancestor::docset/@setid" $file)
  dc=$($starlet sel -t -v "(//deliverable)["$deliverable"]/dc" $file)
  subdeliverables=$(echo -e "$currentdeliverable" | $starlet sel -t -v "//subdeliverable" | sort)
  uniquesubdeliverables=$(echo -e "$subdeliverables" | sort -u)
  [[ ! "$subdeliverables" == "$uniquesubdeliverables" ]] && \
  echo -e \
    "Some subdeliverable elements within a deliverable have non-unique values. Check for occurrences of the following duplicated subdeliverable(s) in docset=$setid/language=$langcode/dc=$dc: "$(comm -2 -3 <(echo -e "$subdeliverables") <(echo -e "$uniquesubdeliverables") | tr '\n' ' ')".\n---"
done

exit 0
