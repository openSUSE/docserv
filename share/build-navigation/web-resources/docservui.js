var body = '';
var productSelect = '';
var versionSelect = '';

var path = basePath + 'docserv/data/'
var productData = 'no_data';

function loadJSON(path, success, error) {
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      if (xhr.status === 200) {
        if (success) {
          success(JSON.parse(xhr.responseText));
        }
      }
      else if (error) {
        error(xhr);
      }
    }
  }
  xhr.open("GET", path, true); // helpful later, to avoid caching issues?: + '?time=' + Date.now()
  // Response type JSON does not work for me somehow because then I need to
  // use xhr.response instead of xhr.responseText above.
  xhr.responseType = 'text';
  xhr.send();
}

function getProductData() {
  loadJSON(path + 'product.json',
    function (data) {
        productData = data;
        populateProductSelect();
    },
    function (xhr) {
      console.error(xhr);
      // do something to tell the user.
    }
  );
}


function populateProductSelect() {
  productSelect.removeChild( productSelect.getElementsByClassName( 'ds-select-instruction' )[0] );
  var productlinelist = Object.keys(productData.productline);
  for (var i = 0; i < productlinelist.length; i++) {
    var link = document.createElement('a');
    link.setAttribute( 'href', '#' + productlinelist[ i ] );
    link.textContent = productData.productline[ Object.keys( productData.productline )[ i ] ];
    productSelect.appendChild( link );
    link.addEventListener('click',function(){
        var links = productSelect.getElementsByTagName( 'a' );
        for (var i = 0; i < links.length; i++) {
          links[i].classList.remove( 'ds-selected' );
        }
        this.classList.add( 'ds-selected' );
        populateVersionSelect(this.hash.substr(1));
    });
  }
}

function populateVersionSelect(productid) {
  var instruction = versionSelect.getElementsByClassName( 'ds-select-instruction' )
  if ( instruction[0] ){
    instruction[0].remove();
  }
  existingLinks = versionSelect.getElementsByTagName( 'a' );
  if ( existingLinks[0] ) {
    // go backwards, to avoid giving the browser hiccups
    for (var i = existingLinks.length - 1; i >= 0; i--) {
      // FIXME: remove() is apparently not supported in IE 11. relevant?
      existingLinks[i].remove();
    }
  }
  var versionlist = Object.keys(productData.product[productid]);
  for (var i = 0; i < versionlist.length; i++) {
    var link = document.createElement('a');
    // FIXME: actually find out the correct language at this point
    link.setAttribute( 'href', basePath + pageLanguage + '/' + versionlist[ i ] + '/index.' + templateExtension);
    var selectedProduct = productData.product[ productid ][ Object.keys( productData.product[productid] )[ i ] ]
    link.textContent = selectedProduct['name'] + ' ' + selectedProduct["version"];
    versionSelect.appendChild( link );
  }
}

function loadDocSet(setid) {
  loadJSON(path + setid + '/' + 'setdata.json',
    function (data) {
        docSetData = data;
        populateDocSet();
    },
    function (xhr) {
      console.error(xhr);
      // do something to tell the user.
    }
  );
}

function populateDocSet() {
  var e_docSetWrap = document.getElementById('docsetwrap');
  var s_product = docSetData.productname + ' ' + docSetData.version;
  var e_title = document.createElement('h2');
  e_title.classList.add('ds-docset-title');
  e_title.textContent = s_product;
  e_docSetWrap.appendChild(e_title);
  var e_desc = document.createElement('div');
  e_desc.classList.add('ds-docset-desc');
  // FIXME: l10n support
  // FIXME: is this at all dangerous? we trust our JSON, right?
  e_desc.innerHTML = docSetData.description[0].description;
  e_docSetWrap.appendChild(e_desc);
  for (var i = 0; i < docSetData.category.length; i++) {
    var e_cat = document.createElement('div');
    e_cat.classList.add('ds-docset-category');
    e_docSetWrap.appendChild(e_cat);
    // FIXME: we probably want to set id=product/set/catid on this div
    if (docSetData.category[i].category != false) {
      var e_catTitle = document.createElement('h3');
      e_catTitle.classList.add('ds-docset-category-title');
      // FIXME: l10n support
      e_catTitle.textContent = docSetData.category[i].title[0].title;
      e_cat.appendChild(e_catTitle);
      // FIXME: needs code to fetch description field
    }
    else {
      e_cat.classList.add('ds-category-no-title');
    };
    var e_documentTable = document.createElement('table');
    e_documentTable.classList.add('ds-docset-table');
    e_cat.appendChild(e_documentTable);
    for (var j = 0; j < docSetData.category[i].document.length; j++) {
      var e_documentRow = document.createElement('tr');
      e_documentTable.appendChild(e_documentRow);

      var e_documentTitle = document.createElement('td');
      e_documentTitle.classList.add('ds-docset-table-title');
      // FIXME: l10n support
      e_documentTitle.textContent = docSetData.category[i].document[j][0].title;
      e_documentRow.appendChild(e_documentTitle);
      var e_documentLanguage = document.createElement('td');
      e_documentLanguage.classList.add('ds-docset-table-language');
      if (docSetData.category[i].document[j].length > 1) {
        var e_languageSelector = document.createElement('select');
        e_documentLanguage.classList.add('ds-has-language-selector');
        e_languageSelector.classList.add('ds-docset-table-lang-select');
        e_documentLanguage.appendChild(e_languageSelector);
        for (var k = 0; k < docSetData.category[i].document[j].length; k++) {
          // FIXME: This currently makes the assumption that the default
          // document language is also the UI language. E.g. if a user is on
          // the French site and there is a document available in French, we
          // probably want to show that by default and not English.
          var e_languageChoice = document.createElement('option');
          e_languageChoice.setAttribute( 'value', docSetData.category[i].document[j][k].lang );
          e_languageChoice.textContent = docSetData.category[i].document[j][k].lang;
          e_languageSelector.appendChild(e_languageChoice);
          // FIXME: The current version ~is pretty~exists but does nothing --
          // evt hdlr ne1?
          e_languageChoice.addEventListener('click',function(){
              // FIXME This is nonsense, e_documentTitle, i, j, and k are gone from this context already
              e_documentTitle.textContent = docSetData.category[i].document[j][k].title;
          });
        };
      }
      else {
        e_documentLanguage.textContent = docSetData.category[i].document[j][0].lang;
      };
      e_documentRow.appendChild(e_documentLanguage);
      var formatList = docSetData.category[i].document[j][0].format;
      var e_documentFormats = document.createElement('td');
      e_documentFormats.classList.add('ds-docset-table-formats');
      e_documentRow.appendChild(e_documentFormats);
      for (var k = 0; k < Object.keys(formatList).length; k++) {
        var e_documentLink = document.createElement('a');
        e_documentLink.classList.add('ds-docset-table-link');
        e_documentLink.textContent = Object.keys(formatList)[k];
        e_documentLink.setAttribute( 'href', basePath + formatList[ Object.keys(formatList)[k] ] );
        e_documentFormats.appendChild(e_documentLink);
      };
    };
  }
}

function dsInit() {
  body = document.getElementsByTagName( 'body' )[0];
  if (pageRole == 'main') {
    productSelect = document.getElementById( 'ds-product-select' );
    versionSelect = document.getElementById( 'ds-version-select' );

    getProductData();
  }
  else if (pageRole == 'product') {
    setid = pageProduct + '/' + pageDocSet;

    loadDocSet(setid);
  };

}
