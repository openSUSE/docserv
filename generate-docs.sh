#!/bin/bash

# requirements
for tool in daps asciidoctor trang mktemp python3; do
  which $tool || { echo "This script needs $tool"; exit 1; }
done

# is this the root of the Ds2 repo?
if [[ ! $(git remote -v | head -1 | grep -oP '/docserv(\.git)? ') ]] || \
  [[ ! $(git rev-parse --show-toplevel) == "$PWD" ]]; then
  echo "You need to be at the root of the Docserv2 repo."
  exit 1
fi

# dirs
ds2dir="$PWD"
tdir=$(mktemp --tmpdir --directory ds2-doc-XXXXXX)

echo $tdir
cd $tdir

  # build schema docs
  git clone https://github.com/openSUSE/rng2doc.git
  cd rng2doc
    rm -rf env 2> /dev/null
    python3 -m venv env
    . env/bin/activate
    pip3 install -U pip setuptools
    pip3 install -r requirements.txt
    ./setup.py develop
  cd -

  trang "$ds2dir/share/validate-product-config/product-config-schema.rnc" "$tdir/product-config.rng"
  [[ $? -eq 0 ]] || { echo "trang conversion build for product config schema failed, giving up."; exit 1; }
  rng2doc -f html --output product-config/index.html product-config.rng
  [[ $? -eq 0 ]] || { echo "rng2doc build for product config schema failed, giving up."; exit 1; }
  sed -ri 's/<a class="navbar-brand" href="#">/<a class="navbar-brand" href="#">Docserv² product configuration: /' product-config/html/{index.html,elements/*.html}

  trang "$ds2dir/share/build-navigation/fragment-l10n-schema.rnc" "$tdir/l10n.rng"
  [[ $? -eq 0 ]] || { echo "trang conversion for l10n schema failed, giving up."; exit 1; }
  rng2doc -f html --output l10n/index.html l10n.rng
  [[ $? -eq 0 ]] || { echo "rng2doc build for l10n schema failed, giving up."; exit 1; }
  sed -ri 's/<a class="navbar-brand" href="#">/<a class="navbar-brand" href="#">Docserv² localization: /' l10n/html/{index.html,elements/*.html}


  # build The Guide
  daps --builddir "$tdir" -d "$ds2dir/docs/DC-docserv" html
  [[ $? -eq 0 ]] || { echo "DAPS build for DC-docserv failed, giving up."; exit 1; }

  br="build-result"
  mkdir "$br"
  mkdir -p $br/schemas
  cp -r l10n/html $br/schemas/l10n
  cp -r product-config/html $br/schemas/product-config
  cp -r docserv/html/docserv $br/docs
  echo "<!DOCTYPE html><html><head><title>Docserv²</title></head><body><h1>Docserv²</h1><a href='docs/'>Guide</a> - <a href='schemas/product-config/'>Product configuration schema</a> - <a href='schemas/l10n/'>Localization file schema</a></body></html>" \
    > "$br/index.html"

cd $ds2dir

git checkout "gh-pages"
rm -rf ./*
cp -r "$tdir/$br/"* .
git add .
git commit -m "Update docs"

echo -e "If you're happy:\n  git push && git checkout -"
