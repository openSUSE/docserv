#!/bin/bash

# make sure that deliverables defined in translations are a subset of the
# deliverables defined in the default language

file=$1

deliverable_xpath="//deliverable[ancestor::language[not(@default) or not(@default='true' or @default='1')]]"
deliverables=$($starlet sel -t -v "count($deliverable_xpath)" $file)
for deliverable in $(seq 1 "$deliverables"); do
  currentdc=$($starlet sel -t -v "($deliverable_xpath)[$deliverable]/dc" $file)
  isdefaultdc=$($starlet sel -t -v "($deliverable_xpath)[$deliverable]/parent::language/preceding-sibling::language[@default='1' or @default='true']/descendant::dc[. = '$currentdc']" $file)
  [[ "$isdefaultdc" ]] || {
    setid=$($starlet sel -t -v "($deliverable_xpath)[$deliverable]/ancestor::docset/@setid" $file)
    language=$($starlet sel -t -v "($deliverable_xpath)[$deliverable]/ancestor::language/@lang" $file)
    echo -e \
      "The DC file $currentdc is configured for docset=$setid/language=$language but not for the default language of docset=$setid. Documents configured for translation languages must be subset of the documents configured for the default language.\n---"
    continue
  }

  this_subdeliverable_xpath="($deliverable_xpath)[$deliverable]/subdeliverable"
  subdeliverables=$($starlet sel -t -v "count($this_subdeliverable_xpath)" $file)
  [[ $subdeliverables -ge 1 ]] || continue
  for subdeliverable in $(seq 1 "$subdeliverables"); do
    current_subdeliverable=$($starlet sel -t -v "($this_subdeliverable_xpath)[$subdeliverable]" $file)
    is_default_subdeliverable=$($starlet sel -t -v "($this_subdeliverable_xpath)[$subdeliverable]/ancestor::language/preceding-sibling::language[@default='1' or @default='true']/descendant::deliverable[dc = '$currentdc']/subdeliverable[. = '$current_subdeliverable']" $file)
    [[ "$is_default_subdeliverable" ]] || {
      setid=$($starlet sel -t -v "(//deliverable[ancestor::language[not(@default or @default='true' or @default='1')]])[$deliverable]/ancestor::docset/@setid" $file)
      language=$($starlet sel -t -v "(//deliverable[ancestor::language[not(@default or @default='true' or @default='1')]])[$deliverable]/ancestor::language/@lang" $file)
      dc=$($starlet sel -t -v "(//deliverable[ancestor::language[not(@default or @default='true' or @default='1')]])[$deliverable]/dc" $file)
      echo -e \
        "The subdeliverable $current_subdeliverable is configured for docset=$setid/language=$language/deliverable=$dc but not for the same deliverable of the default language of docset=$setid. Documents configured for translation languages must be subset of the documents configured for the default language.\n---"
    }
  done
done

exit 0
