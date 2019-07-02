<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common"
  extension-element-prefixes="exsl"
  exclude-result-prefixes="exsl">

  <xsl:include href="string-replace.xsl"/>

  <xsl:variable name="cache_content" select="document($cache_file)/docservcache"/>

  <xsl:param name="pathprefix" select="''"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <!-- Create a list of available products. -->
    <!-- FIXME: We need to cross-check this list against what is available in the cache to avoid showing products that aren't built yet (at least in the public version.) -->
    <exsl:document
     href="{$pathprefix}product.json"
     method="text"
     encoding="UTF-8"
     indent="no"
     media-type="application/x-json">
{
  "productline": {
     <xsl:apply-templates select="//product" mode="generate-productline-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate(name,
           'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))"/>
     </xsl:apply-templates>
  },
  "product": {
     <xsl:apply-templates select="//product" mode="generate-product-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate(name,
           'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))"/>
     </xsl:apply-templates>
  }
}
    </exsl:document>

    <!-- Create individual JSON files for each docset -->
    <xsl:apply-templates select="//docset" mode="generate-docset-json"/>
  </xsl:template>

  <!-- Make sure to exclude products based on lifecycle. -->
  <!-- Make sure to handle SBP differently. -->
  <xsl:template match="product" mode="generate-productline-list">
    "<xsl:value-of select="@productid"/>": "<xsl:value-of select="name"/>",</xsl:template>


  <xsl:template match="product" mode="generate-product-list">
    "<xsl:value-of select="@productid"/>": {<xsl:apply-templates select="docset" mode="generate-product-list">
      <xsl:sort
        lang="en"
        select="normalize-space(translate(version,
          'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))"/>
    </xsl:apply-templates>
    },</xsl:template>

  <!-- Make sure to exclude products based on lifecycle. -->
  <!-- Make sure to handle SBP differently. -->
  <xsl:template match="docset" mode="generate-product-list">
    <xsl:variable name="visible">
      <xsl:choose>
        <xsl:when test="@navigation-visible = 'hidden'">
          <xsl:text>false</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>true</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:variable name="name">
      <xsl:choose>
        <xsl:when test="name">
          <xsl:value-of select="name"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="ancestor::product/name"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

      "<xsl:value-of select="ancestor::product/@productid"/>/<xsl:value-of select="@setid"/>": {
        "setid": "<xsl:value-of select="@setid"/>",
        "visible": <xsl:value-of select="$visible"/>,
        "name": "<xsl:value-of select="$name"/>",
        "shortname": "<xsl:value-of select="ancestor::product/shortname"/>",
        "version": "<xsl:value-of select="version"/>",
        "defaultlanguage": "<xsl:value-of select="builddocs/language[@default='1' or @default='true']/@lang"/>",
        "languages": [<xsl:apply-templates select="builddocs/language[not(@default='1' or @default='true')]" mode="generate-product-list"/>
          ]
      },
  </xsl:template>

  <xsl:template match="language" mode="generate-product-list">
           "<xsl:value-of select="@lang"/>",</xsl:template>

  <xsl:template match="//docset" mode="generate-docset-json">
    <xsl:variable name="name">
      <xsl:choose>
        <xsl:when test="name">
          <xsl:value-of select="name"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="ancestor::product/name"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <!-- FIXME: This file naming is not deterministic enough, e.g.
    productid=blub-12/setid=sp2 would get the same JSON file name as
    productid=blub/setid=12-sp2 == product-blub-12-sp2.json -->
    <exsl:document
     href="{$pathprefix}product-{parent::product/@productid}-{@setid}.json"
     method="text"
     encoding="UTF-8"
     indent="no"
     media-type="application/x-json">
{
  "productname": "<xsl:value-of select="$name"/>",
  "shortname": "<xsl:value-of select="ancestor::product/shortname"/>",
  "version": "<xsl:value-of select="version"/>",
  "description": [
    <xsl:apply-templates select="ancestor::product/desc" mode="generate-docset-json"/>
  ],
  "document": [
    <!-- FIXME: should uncategorized items be listed first or last? -->
    <xsl:call-template select="." mode="generate-docset-json-no-cat"/>
    <xsl:apply-templates select="ancestor::product/category" mode="generate-docset-json"/>
  ]
}
      <!--
      zip: docset.zip
      doc-by-cat
        categoryid-a *** add category sorting key to RNC?
          doc1 [en-us: {html: index.html, single-html: index1.html, epub: file.epub, pdf: file.pdf},
                de-de: {...} ]
     } -->
    </exsl:document>

  </xsl:template>

  <xsl:template match="desc" mode="generate-docset-json">
    <xsl:variable name="default">
      <xsl:choose>
        <xsl:when test="@default = 1 or @default = 'true'">
          <xsl:text>true</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>false</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    {
      "lang": "<xsl:value-of select="@lang"/>",
      "default": <xsl:value-of select="$default"/>,
      "description": "<xsl:apply-templates select="text()|*" mode="escape-html"/>"
    },
  </xsl:template>

  <xsl:template mode="generate-docset-json-no-cat">
    <xsl:if test="descendant::deliverable[not(subdeliverable)][not(@category)] or
                  descendant::subdeliverable[not(@category)] or
                  link[not(@category)]">
      {
        "category": false,
        "name": false,
        "document": [
          <!-- FIXME sort all this stuff alphabetically -->
          <!-- FIXME take into account languages -->
          <xsl:apply-templates select="builddocs[@default = 'true' or @default = 1]/deliverable[not(@category)]"/>
          <!-- FIXME handle subdelivs -->
          <!-- FIXME handle links -->
        ]
      },
    </xsl:if>
  </xsl:template>

  <xsl:template match="category" mode="generate-docset-json">
    <!-- FIXME: categories are not sorted in any way. -->
    <xsl:variable name="used-categories">
      <xsl:text> </xsl:text>
      <xsl:apply-templates select="parent::product/descendant::*[@category]/@category" mode="category-name-list"/>
    </xsl:variable>
    <xsl:if test="contains($used-categories, @categoryid)">
      {
        "category": "<xsl:value-of select="@categoryid"/>",
        "name": [
          <xsl:apply-templates select="name" mode="generate-docset-json"/>
        ],
        "document": [
          <!-- FIXME sort all this stuff alphabetically -->
          <!-- FIXME handle simple delivs -->
          <!-- FIXME handle subdelivs -->
          <!-- FIXME handle links -->
        ]
      },
    </xsl:if>
  </xsl:template>

  <xsl:template match="@category" mode="category-name-list">
    <xsl:value-of select="."/>
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="category/name" mode="generate-docset-json">
    <xsl:variable name="default">
      <xsl:choose>
        <xsl:when test="@default = 1 or @default = 'true'">
          <xsl:text>true</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>false</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
        {
          "lang": "<xsl:value-of select="@lang"/>",
          "default": <xsl:value-of select="$default"/>,
          "localname": "<xsl:value-of select="."/>"
        },
  </xsl:template>


  <!-- HTML-in-JSON escaping -->

  <xsl:template match="*" mode="escape-html">
    <xsl:text>&lt;</xsl:text><xsl:value-of select="local-name(.)"/>
    <xsl:apply-templates select="@*" mode="escape-html"/>
    <xsl:text>&gt;</xsl:text>
    <xsl:apply-templates select="text()|*" mode="escape-html"/>
    <xsl:text>&lt;/</xsl:text><xsl:value-of select="local-name(.)"/><xsl:text>&gt;</xsl:text>
  </xsl:template>

  <xsl:template match="@*" mode="escape-html">
    <xsl:text> </xsl:text><xsl:value-of select="local-name(.)"/><xsl:text>=\&quot;</xsl:text>
    <xsl:call-template name="escape-text">
      <xsl:with-param name="use-single-quote-only" select="true"/>
    </xsl:call-template>
    <xsl:text>\&quot;</xsl:text>
  </xsl:template>

  <xsl:template match="text()" mode="escape-html">
    <xsl:call-template name="escape-text"/>
  </xsl:template>

  <xsl:template name="escape-text" mode="escape-html">
    <xsl:param name="input" select="."/>
    <xsl:param name="use-single-quote-only" select="false"/>

    <!-- Remove deadweight strings that consist of only spaces and newlines -->
    <xsl:variable name="text-remove-empty">
      <xsl:choose>
        <xsl:when test="not(translate($input,' &#10;',''))">
          <xsl:text/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$input"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <!-- Newlines need to be escaped as \\n for JSON. -->
    <xsl:variable name="text-fix-newline">
      <xsl:call-template name="string-replace">
        <xsl:with-param name="input" select="$text-remove-empty"/>
        <xsl:with-param name="search-string" select="'&#10;'"/>
        <xsl:with-param name="replace-string" select="'\\n'"/>
      </xsl:call-template>
    </xsl:variable>

    <!-- Replace literal backslashes -->
    <xsl:variable name="text-fix-backslash">
      <xsl:call-template name="string-replace">
        <xsl:with-param name="input" select="$text-fix-newline"/>
        <xsl:with-param name="search-string" select="'\'"/>
        <xsl:with-param name="replace-string" select="'\\'"/>
      </xsl:call-template>
    </xsl:variable>

    <!-- Quotes are used to delimit strings in JSON. -->
    <xsl:variable name="text-fix-quote">
      <xsl:choose>
        <xsl:when test="$use-single-quote-only = true">
          <xsl:call-template name="string-replace">
            <xsl:with-param name="input" select="$text-fix-newline"/>
            <xsl:with-param name="search-string" select="'&quot;'"/>
            <xsl:with-param name="replace-string" select='"&apos;"'/>
          </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
          <xsl:call-template name="string-replace">
            <xsl:with-param name="input" select="$text-fix-newline"/>
            <xsl:with-param name="search-string" select="'&quot;'"/>
            <xsl:with-param name="replace-string" select="'\&quot;'"/>
          </xsl:call-template>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="$text-fix-quote"/>
  </xsl:template>

</xsl:stylesheet>
