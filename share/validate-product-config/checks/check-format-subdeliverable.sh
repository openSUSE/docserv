#!/bin/bash

# make sure that deliverables that contain subdeliverables only enable html
# or single-html as format
# it would actually be possible to catch this issue via the RNC -- just either
# disable the @pdf and @epub attributes; the only issue is that the error
# messages would be much harder to understand. so let's keep this check for
# the moment.

file=$1

deliverables=$($starlet sel -t -v "count(//deliverable[subdeliverable])" $file | sort)
for deliverable in $(seq 1 "$deliverables"); do
  hasbadformat=$($starlet sel -t -v "(//deliverable[subdeliverable])[$deliverable]/format/@*[local-name(.) = 'epub' or local-name(.) = 'pdf'][. = 'true' or . = '1']" $file)
  [[ "$hasbadformat" ]] && {
    setid=$($starlet sel -t -v "(//deliverable[subdeliverable])[$deliverable]/ancestor::docset/@setid" $file)
    language=$($starlet sel -t -v "(//deliverable[subdeliverable])[$deliverable]/ancestor::language/@lang" $file)
    dc=$($starlet sel -t -v "(//deliverable[subdeliverable])[$deliverable]/dc" $file)
    echo -e \
      "A deliverable that has subdeliverables has PDF or EPUB enabled as a format: docset=$setid/language=$language/deliverable=$dc. subdeliverables are only supported for the formats HTML and Single-HTML.\n---"
 }
done

exit 0
