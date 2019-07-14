<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet
[
  <!ENTITY sortlower "abcdefghijklmnopqrstuvwxyz">
  <!ENTITY sortupper "ABCDEFGHIJKLMNOPQRSTUVWXYZ">
]>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common"
  xmlns:dscr="https://github.com/openSUSE/docserv/docserv2_cache_result"
  extension-element-prefixes="exsl"
  exclude-result-prefixes="exsl dscr">

  <xsl:include href="string-replace.xsl"/>
  <xsl:include href="cache-request.xsl"/>
  <xsl:include href="escape-html.xsl"/>

  <xsl:param name="output_root">
    <xsl:message terminate="yes">Root directory for output is missing.</xsl:message>
  </xsl:param>
  <xsl:param name="cache_file">
    <xsl:message terminate="yes">Stitched document cache file XSLT parameter missing.</xsl:message>
  </xsl:param>
  <xsl:param name="ui_languages">
    <xsl:message terminate="yes">UI languages XSLT parameter missing.</xsl:message>
  </xsl:param>

  <xsl:param name="product">
    <xsl:message terminate="yes">Product parameter missing.</xsl:message>
  </xsl:param>
  <xsl:param name="docset">
    <xsl:message terminate="yes">Docset parameter missing.</xsl:message>
  </xsl:param>
  <xsl:param name="internal_mode" select="'false'"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <!-- Create a list of available products. -->
    <!-- FIXME: We need to cross-check this list against what is available in the cache to avoid showing products that aren't built yet (at least in the public version.) -->
    <exsl:document
      href="{$output_root}product.json"
      method="text"
      encoding="UTF-8"
      indent="no"
      media-type="application/x-json">
{
  "productline": {
     <xsl:apply-templates select="//product" mode="generate-productline-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate(name, '&sortlower;', '&sortupper;'))"/>
     </xsl:apply-templates>
  },
  "product": {
     <xsl:apply-templates select="//product" mode="generate-product-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate(name,'&sortlower;', '&sortupper;'))"/>
     </xsl:apply-templates>
  }
}
    </exsl:document>

    <!-- Create individual JSON files for each docset -->
    <xsl:apply-templates select="//docset" mode="generate-docset-json"/>
  </xsl:template>

  <!-- FIXME: Make sure to exclude products based on lifecycle. -->
  <!-- FIXME: Make sure to handle SBP differently. -->
  <xsl:template match="product" mode="generate-productline-list">
    "<xsl:value-of select="@productid"/>": "<xsl:value-of select="name"/>",</xsl:template>


  <xsl:template match="product" mode="generate-product-list">
    "<xsl:value-of select="@productid"/>": {<xsl:apply-templates select="docset" mode="generate-product-list">
      <!-- FIXME: sort translate() lists need to be expanded for other langs. -->
      <xsl:sort
        lang="en"
        select="normalize-space(translate(version,
          '&sortlower;', '&sortupper;'))"/>
    </xsl:apply-templates>
    },</xsl:template>

  <!-- FIXME: Make sure to exclude products based on lifecycle. -->
  <!-- FIXME: Make sure to handle SBP differently. -->
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
        "defaultlanguage": "<xsl:value-of select="builddocs/language[@default='true']/@lang"/>",
        "languages": [<xsl:apply-templates select="builddocs/language[not(@default='true')]" mode="generate-product-list"/>
          ]
      },
  </xsl:template>

  <xsl:template match="language" mode="generate-product-list">
           "<xsl:value-of select="@lang"/>",</xsl:template>

  <xsl:template match="docset" mode="generate-docset-json">
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

    <exsl:document
     href="{$output_root}{parent::product/@productid}/{@setid}/setdata.json"
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
  "category": [
    <xsl:apply-templates select="ancestor::product/category" mode="generate-docset-json">
      <xsl:with-param name="node" select="."/>
    </xsl:apply-templates>
    <xsl:call-template select="." name="generate-docset-json-no-cat"/>
  ]
}
      <!--
      zip: docset-en-us.zip, docset-de-de.zip
      -->
    </exsl:document>

  </xsl:template>

  <xsl:template match="desc" mode="generate-docset-json">
    {
      "lang": "<xsl:value-of select="@lang"/>",
      "default":  <xsl:call-template name="determine-default"/>,
      "description": "<xsl:apply-templates select="text()|*" mode="escape-html"/>"
    },
  </xsl:template>

  <xsl:template name="generate-docset-json-no-cat">
    <xsl:if test="descendant::deliverable[not(subdeliverable)][not(@category)] or
                  descendant::subdeliverable[not(@category)] or
                  descendant::link[not(@category)]">
      <xsl:variable name="documents-candidate">
        <xsl:apply-templates
          select="( builddocs/language[@default = 'true']/deliverable[not(subdeliverable)][not(@category)] |
                    builddocs/language[@default = 'true']/deliverable/subdeliverable[not(@category)] )"
          mode="generate-docset-json"/>
        <xsl:apply-templates select="extralinks/link[not(@category)]" mode="generate-docset-json"/>
      </xsl:variable>
      <xsl:variable name="documents">
        <xsl:call-template name="dedupe-documents">
          <xsl:with-param name="documents-in" select="exsl:node-set($documents-candidate)"/>
        </xsl:call-template>
      </xsl:variable>

      <xsl:call-template name="json-category-definition" mode="generate-docset-json">
        <xsl:with-param name="is-actual-category" select="'false'"/>
        <xsl:with-param name="documents" select="$documents"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template match="category" mode="generate-docset-json">
    <xsl:param name="node" select="."/>
    <xsl:variable name="categoryid" select="concat(' ', @categoryid, ' ')"/>
    <!-- FIXME: categories are not yet sorted in any way. wondering whether
    to sort alphabetically, implicitly by order in the config document or
    explicitly with rank attribute. -->
    <xsl:variable name="used-categories">
      <xsl:text> </xsl:text>
      <xsl:apply-templates select="parent::product/descendant::*[@category]/@category" mode="category-name-list"/>
    </xsl:variable>
    <xsl:if test="contains($used-categories, $categoryid)">
      <xsl:variable name="documents-candidate">
        <xsl:apply-templates
          select="( $node/builddocs/language[@default = 'true']/deliverable[not(subdeliverable)][contains(concat(' ', @category,' '), $categoryid)] |
                    $node/builddocs/language[@default = 'true']/deliverable/subdeliverable[contains(concat(' ',@category,' '), $categoryid)] )"
          mode="generate-docset-json"/>
        <xsl:apply-templates select="$node/extralinks/link[contains(concat(' ',@category,' '), $categoryid)]" mode="generate-docset-json"/>
      </xsl:variable>
      <xsl:variable name="documents">
        <xsl:call-template name="dedupe-documents">
          <xsl:with-param name="documents-in" select="exsl:node-set($documents-candidate)"/>
        </xsl:call-template>
      </xsl:variable>

      <xsl:call-template name="json-category-definition" mode="generate-docset-json">
        <xsl:with-param name="is-actual-category" select="'true'"/>
        <xsl:with-param name="categoryid" select="@categoryid"/>
        <xsl:with-param name="documents" select="$documents"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template name="dedupe-documents">
    <xsl:param name="documents-in" select="''"/>
    <xsl:param name="count" select="1"/>
    <xsl:param name="known-hashes" select="' '"/>
    <xsl:if test="not(contains($known-hashes, concat(' ', $documents-in/dscr:jsondocument[$count]/@hash, ' ')))">
      <dscr:jsondocument title="{$documents-in/dscr:jsondocument[$count]/@title}" hash="{$documents-in/dscr:jsondocument[$count]/@hash}">
        <xsl:value-of select="$documents-in/dscr:jsondocument[$count]"/>
      </dscr:jsondocument>
    </xsl:if>
    <xsl:if test="$documents-in/dscr:jsondocument[$count + 1]">
      <xsl:call-template name="dedupe-documents">
        <xsl:with-param name="documents-in" select="$documents-in"/>
        <xsl:with-param name="count" select="$count + 1"/>
        <xsl:with-param name="known-hashes" select="concat($known-hashes, ' ', $documents-in/dscr:jsondocument[$count]/@hash, ' ')"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template name="json-category-definition" mode="generate-docset-json">
    <xsl:param name="is-actual-category" select="'true'"/>
    <xsl:param name="categoryid" select="@categoryid"/>
    <xsl:param name="documents" select="$documents"/>

    <xsl:if test="$documents != ''">
      {
        <xsl:choose>
          <xsl:when test="$is-actual-category != 'false'">
        "category": "<xsl:value-of select="$categoryid"/>",
        "title": [
          <xsl:apply-templates select="name" mode="generate-docset-json"/>
        ],
          </xsl:when>
          <xsl:otherwise>
        "category": false,
        "title": false,
          </xsl:otherwise>
        </xsl:choose>
        "document": [
        <xsl:for-each select="exsl:node-set($documents)/dscr:jsondocument">
          <xsl:sort
            lang="en"
            select="normalize-space(translate(@title,'&sortlower;', '&sortupper;'))"/>
          <xsl:value-of select="."/>
        </xsl:for-each>
        ]
      },
    </xsl:if>
  </xsl:template>

  <xsl:template match="@category" mode="category-name-list">
    <xsl:value-of select="."/>
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="category/name" mode="generate-docset-json">
        {
          "lang": "<xsl:value-of select="@lang"/>",
          "default":  <xsl:call-template name="determine-default"/>,
          "localname": "<xsl:value-of select="."/>"
        },
  </xsl:template>

  <xsl:template match="deliverable[not(subdeliverable)]|subdeliverable" mode="generate-docset-json">
    <xsl:param name="node" select="."/>
    <xsl:param name="lang" select="ancestor::language/@lang"/>
    <xsl:param name="default">
      <xsl:call-template name="determine-default">
        <xsl:with-param name="node" select="ancestor::language"/>
      </xsl:call-template>
    </xsl:param>

    <xsl:variable name="title">
      <xsl:call-template name="cache-request">
        <xsl:with-param name="information" select="'title'"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="title-escaped">
      <xsl:apply-templates select="exsl:node-set($title)" mode="escape-html"/>
    </xsl:variable>
    <xsl:variable name="hash">
      <xsl:call-template name="cache-request">
        <xsl:with-param name="information" select="'hash'"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="hash-match">
      <xsl:choose>
        <xsl:when test="$hash != ''">
          <xsl:call-template name="cache-hash-match">
            <xsl:with-param name="hash" select="$hash"/>
          </xsl:call-template>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>

    <xsl:variable name="content">
      <xsl:if test="$hash != ''">
              {
                "lang": "<xsl:value-of select="$lang"/>",
                "default": <xsl:value-of select="$default"/>,
                "title": "<xsl:value-of select="$title-escaped"/>",
                "format": {
                <xsl:for-each select="exsl:node-set($hash-match)/dscr:result">
                  <!-- Let's sort formats by their (likely) importance:
                  HTML, Single-HTML, PDF, EPUB with this one werid trick!
                  Luckily, they all start with a different letter, otherwise
                  this might have become icky. -->
                  <xsl:sort lang="en" select="normalize-space(translate(@format, 'hHsSpPeEoO', '1122334455'))"/>
                  <!-- NB: We intentionally accept _any_ DC file with the
                  right @format from the same product below. This allows us
                  to group builds of sets (HTML) together with builds of
                  individual books (Single-HTML, PDF, EPUB).-->
                  <xsl:variable name="format" select="@format"/>
                  <xsl:if
                    test="
                      $node/ancestor::product/@productid = @productid and
                      $node/ancestor::docset/@setid = @setid and
                      $node/ancestor::language/@lang = @lang and
                      $node/ancestor::language/deliverable[format/@*[local-name($format)] = 'true']/dc = @dc
                    ">
                  "<xsl:value-of select="@format"/>": "<xsl:value-of select="@path"/>",
                  </xsl:if>
                </xsl:for-each>
                }
              },
      </xsl:if>
    </xsl:variable>

    <!-- If the document has no cache value, it can't have been built yet, don't
    reference it here. -->
    <!-- FIXME Think about whether internal-mode should affect this 'choose'. -->
    <xsl:choose>
      <xsl:when test="$content != '' and $default = 'true'">
        <xsl:variable name="equivalent-dcs">
          <xsl:text> </xsl:text>
          <xsl:for-each select="exsl:node-set($hash-match)/dscr:result">
            <xsl:value-of select="concat(@dc,'/',@rootid)"/><xsl:text> </xsl:text>
          </xsl:for-each>
        </xsl:variable>
        <dscr:jsondocument title="{$title-escaped}" hash="{$hash}">
            [
              <xsl:value-of select="$content"/>
              <!-- for each non-default lang call this template but with a
              parameter that prevents dscr + outer json thing -->
              <xsl:apply-templates select="ancestor::builddocs/language[not(@default = 'true')]" mode="fatedtopretend">
                <xsl:sort lang="en" select="normalize-space(translate(@lang, '&sortlower;', '&sortupper;'))"/>
                <xsl:with-param name="node" select="$node"/>
                <xsl:with-param name="equivalent-dcs" select="$equivalent-dcs"/>
              </xsl:apply-templates>
            ],
        </dscr:jsondocument>
      </xsl:when>
      <xsl:when test="$content != ''">
        <xsl:value-of select="$content"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="language[not(@default = 'true')]" mode="fatedtopretend">
    <xsl:param name="node" select="."/>
    <xsl:param name="equivalent-dcs" select="$equivalent-dcs"/>

    <!-- From the default-language version, we know already which documents are
    equivalent to which others. Now, it can happen that some specific document
    builds in the default language but not in a translation. But an equivalent
    document providing a different set of formats may have built.
    If we're catching the document that does not build only here, we're a bit
    screwed. So let's make sure to try all the documents we know to be
    equivalent! -->
    <!-- First try to see if there are equivalent subdeliverables -->
    <xsl:variable name="try-subdeliverables">
      <xsl:if test="deliverable/subdeliverable[contains($equivalent-dcs, concat(' ', parent::deliverable/dc,'/',., ' '))]">
        <xsl:apply-templates
          select="deliverable/subdeliverable[contains($equivalent-dcs, concat(' ', parent::deliverable/dc,'/',., ' '))]"
          mode="generate-docset-json"/>
      </xsl:if>
    </xsl:variable>

    <!-- If we don't have a result on the subdeliverables, try regular
    deliverables. If we don't have anything there, there either is no
    translation for this document in that language or it has not been built
    yet. -->
    <xsl:choose>
      <xsl:when test="$try-subdeliverables != ''">
        <xsl:value-of select="$try-subdeliverables"/>
      </xsl:when>
      <xsl:when test="deliverable[not(subdeliverable)][contains($equivalent-dcs, concat(' ', dc,'/'))]">
        <xsl:apply-templates
          select="deliverable[not(subdeliverable)][contains($equivalent-dcs, concat(' ', dc,'/'))]"
          mode="generate-docset-json"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="extralinks/link" mode="generate-docset-json">
    <xsl:variable name="title-escaped-default">
      <xsl:call-template name="escape-text" mode="escape-html">
        <xsl:with-param name="input" select="language[default='true']/@title"/>
      </xsl:call-template>
    </xsl:variable>
          <dscr:jsondocument title="{$title-escaped-default}" hash="link-{generate-id(.)}">
            [
            <xsl:for-each select="language">
              <xsl:variable name="title-escaped">
                <xsl:call-template name="escape-text" mode="escape-html">
                  <xsl:with-param name="input" select="@title"/>
                </xsl:call-template>
              </xsl:variable>
              {
                "lang": "<xsl:value-of select="@lang"/>",
                "default": <xsl:call-template name="determine-default"/>,
                "title": "<xsl:value-of select="$title-escaped"/>",
                "format": {
                <xsl:for-each select="url">
                  "<xsl:value-of select="@format"/>": "<xsl:value-of select="@href"/>",
                </xsl:for-each>
                }
              },
            </xsl:for-each>
            ],
          </dscr:jsondocument>
  </xsl:template>

  <xsl:template name="determine-default">
    <xsl:param name="node" select="."/>
    <xsl:choose>
      <xsl:when test="$node/@default = 'true'">
        <xsl:text>true</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>false</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
