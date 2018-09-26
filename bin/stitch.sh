#!/bin/bash
# $1 - Directory with config files
# $2 - Output file (optional, if not set, outputs to stdout)

out() {
  >&2 echo "$1"
  exit 1
}

starlet='xmlstarlet'

[[ ! -d $1 ]] && out "Directory $1 does not exist"

indir=$1

cd $indir

for file in *.xml; do
  [[ $(2>&1 xmllint --noout --noent $file) ]] && out "$indir/$file is not well-formed."
done

outfile='<?xml version="1.0" encoding="UTF-8"?>\n<docservconfig>\n\n'

for file in *.xml; do
  outfile+=$($starlet sel -t -c "/*" $file)
  outfile+='\n'
done

outfile+='\n</docservconfig>\n'

cd -

if [[ $2 ]]; then
  echo -e "$outfile" > $2
else
  echo -e "$outfile"
fi

# FIXME: Now validate according to DTD/RNG (which we currently don't have)
