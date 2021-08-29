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
  <xsl:include href="relevant-docs.xsl"/>
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

  <xsl:param name="titleformat_deliverable">title subtitle</xsl:param>
  <xsl:param name="titleformat_link">title</xsl:param>
  <xsl:param name="titleformat_deliverable_reference">title subtitle docset</xsl:param>
  <xsl:param name="titleformat_link_reference">title docset</xsl:param>


  <xsl:variable name="existing-sets-supported">
    <xsl:call-template name="list-existing-sets"/>
  </xsl:variable>

  <xsl:variable name="existing-sets-unsupported">
    <xsl:call-template name="list-existing-sets">
      <xsl:with-param name="list" select="'unsupported'"/>
    </xsl:call-template>
  </xsl:variable>


  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <!-- Create a list of available products. -->
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
         select="normalize-space(translate((name|sortname)[last()], '&sortlower;', '&sortupper;'))"/>
     </xsl:apply-templates>
  },
  "product": {
     <xsl:apply-templates select="//product" mode="generate-product-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate((name|sortname)[last()],'&sortlower;', '&sortupper;'))"/>
     </xsl:apply-templates>
  }
}
    </exsl:document>

    <exsl:document
      href="{$output_root}unsupported.json"
      method="text"
      encoding="UTF-8"
      indent="no"
      media-type="application/x-json">
{
  "productline": {
     <xsl:apply-templates select="//product" mode="generate-productline-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate((name|sortname)[last()], '&sortlower;', '&sortupper;'))"/>
       <xsl:with-param name="list" select="$existing-sets-unsupported"/>
     </xsl:apply-templates>
  },
  "product": {
     <xsl:apply-templates select="//product" mode="generate-product-list">
       <xsl:sort
         lang="en"
         select="normalize-space(translate((name|sortname)[last()],'&sortlower;', '&sortupper;'))"/>
       <xsl:with-param name="list" select="$existing-sets-unsupported"/>
     </xsl:apply-templates>
  }
}
    </exsl:document>

    <!-- Create individual JSON files for each docset -->
    <xsl:apply-templates select="//docset" mode="generate-docset-json"/>
  </xsl:template>

  <!-- FIXME: Make sure to handle SBP differently. -->
  <xsl:template match="product" mode="generate-productline-list">
    <xsl:param name="list" select="$existing-sets-supported"/>
    <xsl:if test="contains($list, concat(' ',@productid,'/'))">
    "<xsl:value-of select="@productid"/>": "<xsl:value-of select="name"/>",</xsl:if>
  </xsl:template>


  <xsl:template match="product" mode="generate-product-list">
    <xsl:param name="list" select="$existing-sets-supported"/>
    <xsl:if test="contains($list, concat(' ',@productid,'/'))">
    "<xsl:value-of select="@productid"/>": {<xsl:apply-templates select="docset" mode="generate-product-list">
      <!-- FIXME: sort translate() lists need to be expanded for other langs. -->
      <xsl:sort
        lang="en"
        order="descending"
        select="normalize-space(translate(version,
          '&sortlower;', '&sortupper;'))"/>
      <xsl:with-param name="list" select="$list"/>
    </xsl:apply-templates>
    },</xsl:if>
  </xsl:template>

  <!-- FIXME: Make sure to handle SBP differently. -->
  <xsl:template match="docset" mode="generate-product-list">
    <xsl:param name="list" select="$existing-sets-supported"/>
    <xsl:variable name="visible">
      <xsl:choose>
        <xsl:when test="@navigation = 'hidden' or @navigation = 'disabled'">
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
    <xsl:if test="contains($list, concat(' ',ancestor::product/@productid,'/',@setid,' '))">
      "<xsl:value-of select="ancestor::product/@productid"/>/<xsl:value-of select="@setid"/>": {
        "setid": "<xsl:value-of select="@setid"/>",
        "visible": <xsl:value-of select="$visible"/>,
        "name": "<xsl:value-of select="$name"/>",
        "acronym": "<xsl:value-of select="ancestor::product/acronym"/>",
        "version": "<xsl:value-of select="version"/>",
        "lifecycle": "<xsl:value-of select="@lifecycle"/>"
      },
    </xsl:if>
  </xsl:template>

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

    <xsl:if test="(ancestor::product/@productid = $product and @setid = $docset)">
      <exsl:document
        href="{$output_root}{parent::product/@productid}/{@setid}/setdata.json"
        method="text"
        encoding="UTF-8"
        indent="no"
        media-type="application/x-json">
{
  "productname": "<xsl:value-of select="$name"/>",
  "acronym": "<xsl:value-of select="ancestor::product/acronym"/>",
  "version": "<xsl:value-of select="version"/>",
  "lifecycle": "<xsl:value-of select="@lifecycle"/>",
  "description": [
    <xsl:apply-templates select="ancestor::product/desc" mode="generate-docset-json"/>
  ],
  "category": [
    <xsl:apply-templates select="ancestor::product/category" mode="generate-docset-json">
      <xsl:with-param name="node" select="."/>
    </xsl:apply-templates>
    <xsl:call-template select="." name="generate-docset-json-no-cat"/>
  ],
  "archive": [
    <xsl:call-template name="zip-cache"/>
  ]
}
      </exsl:document>
    </xsl:if>

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
                  descendant::ref[not(@category)] or
                  descendant::link[not(@category)]">
      <xsl:variable name="documents-candidate">
        <xsl:apply-templates
          select="( builddocs/language[@default = 'true']/deliverable[not(subdeliverable)][not(@category)] |
                    builddocs/language[@default = 'true']/deliverable/subdeliverable[not(@category)] )"
          mode="generate-docset-json"/>
        <xsl:apply-templates select="internal/ref[not(@category)]" mode="generate-docset-json"/>
        <xsl:apply-templates select="external/link[not(@category)]" mode="generate-docset-json"/>
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
    <!-- Categories are sorted by order of appearance, not alphabetically and
    not by an explicit ranking attribute. Seems like a good (lazy) solution. -->
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
        <xsl:apply-templates select="$node/internal/ref[contains(concat(' ',@category,' '), $categoryid)]" mode="generate-docset-json"/>
        <xsl:apply-templates select="$node/external/link[contains(concat(' ',@category,' '), $categoryid)]" mode="generate-docset-json"/>
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
          <xsl:apply-templates select="language" mode="generate-docset-json"/>
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

  <xsl:template match="category/language" mode="generate-docset-json">
        {
          "lang": "<xsl:value-of select="@lang"/>",
          "default": <xsl:call-template name="determine-default"/>,
          "title": "<xsl:value-of select="@title"/>",
          "description": <xsl:choose>
            <xsl:when test="*">
              <xsl:text>"</xsl:text>
              <xsl:apply-templates select="text()|*" mode="escape-html"/>
              <xsl:text>"</xsl:text>
            </xsl:when>
            <xsl:otherwise>
              <xsl:text>false</xsl:text>
            </xsl:otherwise>
          </xsl:choose>
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
    <xsl:param name="titleformat">
      <xsl:choose>
        <xsl:when test="@titleformat"><xsl:value-of select="@titleformat"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="$titleformat_deliverable"/></xsl:otherwise>
      </xsl:choose>
    </xsl:param>
    <xsl:variable name="titleformat-spaced" select="concat(' ', $titleformat,' ')"/>

    <xsl:variable name="title-title">
      <xsl:call-template name="cache-request">
        <xsl:with-param name="information" select="'title'"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="title-subtitle">
      <xsl:if test="contains($titleformat-spaced, ' subtitle ')">
        <xsl:call-template name="cache-request">
          <xsl:with-param name="information" select="'subtitle'"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:variable>
    <xsl:variable name="title-docset">
      <xsl:if test="contains($titleformat-spaced, ' docset ')">
        <xsl:call-template name="docset-title"/>
      </xsl:if>
    </xsl:variable>
    <xsl:variable name="title-product">
      <xsl:if test="contains($titleformat-spaced, ' product ')">
        <xsl:call-template name="cache-request">
          <xsl:with-param name="information" select="'product-from-document'"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:variable>

    <xsl:variable name="title-assembled">
      <xsl:if test="string-length(concat($title-docset,$title-product)) &gt; 0">
        <xsl:value-of select="$title-docset"/>
        <!-- docset and product components are currently mutually exclusive.
        The following if only provisions for when that is ever not the case. -->
        <xsl:if test="(string-length($title-docset) &gt; 0) and (string-length($title-product) &gt; 0)">
          <xsl:text> / </xsl:text>
        </xsl:if>
        <xsl:value-of select="$title-product"/>
        <xsl:text>: </xsl:text>
      </xsl:if>
      <xsl:value-of select="$title-title"/>
      <xsl:if test="string-length($title-subtitle) &gt; 0">
        <xsl:text> - </xsl:text>
        <xsl:value-of select="$title-subtitle"/>
      </xsl:if>
    </xsl:variable>

    <xsl:variable name="title-escaped">
      <xsl:apply-templates select="exsl:node-set($title-assembled)" mode="escape-html"/>
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
                "lang-switchable": true,
                "format": {
                <xsl:for-each select="exsl:node-set($hash-match)/dscr:result">
                  <!-- Sort formats by their (likely) importance with THIS
                  ONE WEIRD TRICK!: 1-HTML, 2-Single-HTML, 3-PDF, 4-EPUB, 5-ZIP, 6-TAR, 7-other
                  Luckily, the formats all start with a different letter, otherwise
                  this might have become icky. -->
                  <xsl:sort lang="en" select="normalize-space(translate(@format, 'hHsSpPeEzZtToO', '11223344556677'))"/>
                  <!-- NB: We intentionally accept _any_ DC file with the
                  right @format from the same product below. This allows us
                  to group builds of sets (HTML) together with builds of
                  individual books (Single-HTML, PDF, EPUB).-->
                  <xsl:variable name="format" select="@format"/>

                  <!-- As an input value, "other" makes sense - it's a type
                  of file that is otherwise not supported for linking.
                  However, reading "other" on the output page as a download
                  link might be a bit disorienting, hence just use "file".
                  That is still bad but arguably more descriptive. -->
                  <xsl:variable name="format-out">
                    <xsl:choose>
                      <xsl:when test="@format = 'other'">
                        <xsl:text>file</xsl:text>
                      </xsl:when>
                      <xsl:otherwise>
                        <xsl:value-of select="@format"/>
                      </xsl:otherwise>
                    </xsl:choose>
                  </xsl:variable>

                  <xsl:if
                    test="
                      $node/ancestor::product/@productid = @productid and
                      $node/ancestor::docset/@setid = @setid and
                      $node/ancestor::language/@lang = @lang and
                      $node/ancestor::language/deliverable[format/@*[local-name($format)] = 'true']/dc = @dc
                    ">
                  "<xsl:value-of select="$format-out"/>": "<xsl:value-of select="@path"/>",
                  </xsl:if>
                </xsl:for-each>
                },
                "date": "<xsl:value-of select="(exsl:node-set($hash-match)/dscr:result[
                      @productid = $node/ancestor::product/@productid and
                      @setid = $node/ancestor::docset/@setid and
                      @lang = $node/ancestor::language/@lang
                      ]/@date)[1]"/>"
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
              <!-- for each non-default lang call, run this template but with a
              parameter that prevents dscr + outer json thing -->
              <xsl:apply-templates select="ancestor::builddocs/language[not(@default = 'true')]" mode="get-translated-versions">
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

  <xsl:template match="language[not(@default = 'true')]" mode="get-translated-versions">
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

  <xsl:template match="internal/ref" mode="generate-docset-json">
    <xsl:variable name="product" select="@product"/>
    <xsl:variable name="docset" select="@docset"/>
    <xsl:variable name="dc" select="@dc"/>
    <xsl:variable name="subdeliverable" select="@subdeliverable"/>
    <xsl:variable name="link" select="@link"/>
    <xsl:variable name="titleformat">
      <xsl:choose>
        <xsl:when test="@titleformat"><xsl:value-of select="@titleformat"/></xsl:when>
        <xsl:when test="$dc != ''"><xsl:value-of select="$titleformat_deliverable_reference"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="$titleformat_link_reference"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:choose>
      <xsl:when test="$link != ''">
        <xsl:apply-templates select="(//product[@productid = $product]/docset[@setid = $docset]/external/link[@linkid = $link])[1]" mode="generate-docset-json">
          <xsl:with-param name="titleformat" select="$titleformat"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:when test="$subdeliverable != ''">
        <xsl:apply-templates select="(//product[@productid = $product]/docset[@setid = $docset]/builddocs/language[@default = 'true']/deliverable[dc = $dc]/subdeliverable[. = $subdeliverable])[1]" mode="generate-docset-json">
          <xsl:with-param name="titleformat" select="$titleformat"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:when test="$dc != ''">
        <xsl:apply-templates select="(//product[@productid = $product]/docset[@setid = $docset]/builddocs/language[@default = 'true']/deliverable[dc = $dc])[1]" mode="generate-docset-json">
          <xsl:with-param name="titleformat" select="$titleformat"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:when test="$docset != ''">
        <xsl:call-template name="internal-ref-docset">
          <xsl:with-param name="product" select="$product"/>
          <xsl:with-param name="docset" select="$docset"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:when test="$product != ''">
        <xsl:call-template name="internal-ref-docset">
          <xsl:with-param name="product" select="$product"/>
          <xsl:with-param name="docset" select="//product[@productid = $product]/docset[@default = 'true']/@setid"/>
        </xsl:call-template>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

  <xsl:template name="internal-ref-docset" mode="generate-docset-json">
    <xsl:param name="product" select="''"/>
    <xsl:param name="docset" select="''"/>
    <!-- FIXME: These titles would be way better if they included something
    like "Documentation for ..." instead of just being the name of the
    docset. However, that would necessitate enabling localization here. Our UI
    localization story is currently dodgy (read: non-existent) anyhow, so... -->
    <xsl:variable name="title-default">
      <xsl:call-template name="docset-title">
        <xsl:with-param name="node" select="//product[@productid = $product]/docset[@setid = $docset]/*[1]"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="title-escaped-default">
      <xsl:call-template name="escape-text" mode="escape-html">
        <xsl:with-param name="input" select="$title-default"/>
      </xsl:call-template>
    </xsl:variable>
          <dscr:jsondocument title="{$title-escaped-default}" hash="link-{generate-id(.)}">
            [
              <xsl:call-template name="internal-ref-docset-lang">
                <xsl:with-param name="title" select="$title-escaped-default"/>
                <xsl:with-param name="product" select="$product"/>
                <xsl:with-param name="docset" select="$docset"/>
              </xsl:call-template>
            ],
          </dscr:jsondocument>
  </xsl:template>

  <xsl:template name="internal-ref-docset-lang" mode="generate-docset-json">
    <xsl:param name="title" select="''"/>
    <xsl:param name="product" select="''"/>
    <xsl:param name="docset" select="''"/>
    <xsl:param name="languages" select="concat($ui_languages, ' ')"/>
    <xsl:variable name="default">
      <!-- We'll assume that the default UI language is the one first
      mentioned in $ui_languages. We iterate recursively, so our $languages
      string is getting shorter. Hence, when $ui_languages == $languages, we
      are on the first element. -->
      <xsl:choose>
        <xsl:when test="$languages = concat($ui_languages, ' ')">true</xsl:when>
        <xsl:otherwise>false</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="language">
      <xsl:value-of select="substring-before($languages, ' ')"/>
    </xsl:variable>

              {
                "lang": "<xsl:value-of select="$language"/>",
                "default": <xsl:value-of select="$default"/>,
                "title": "<xsl:value-of select="$title"/>",
                "lang-switchable": false,
                "format": {
                  <!-- FIXME: Not completely happy that we are generating a link
                  path here. There are a ton of assumptions about URL
                  structure here. We don't even know whether it is index.php
                  or index.html that we should be linking to. -->
                  "html": "<xsl:value-of select="concat($language,'/',$product,'/', $docset, '/')"/>",
                },
                "date": false
              },
    <xsl:if test="substring-after($languages, ' ')">
      <xsl:call-template name="internal-ref-docset-lang">
        <xsl:with-param name="title" select="$title"/>
        <xsl:with-param name="product" select="$product"/>
        <xsl:with-param name="docset" select="$docset"/>
        <xsl:with-param name="languages" select="substring-after($languages, ' ')"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template match="external/link" mode="generate-docset-json">
    <xsl:param name="docset-title-inject" select="0"/>

    <xsl:variable name="injected-title">
      <xsl:if test="$docset-title-inject = 1">
        <xsl:call-template name="docset-title"/>
      </xsl:if>
    </xsl:variable>
    <xsl:variable name="title-escaped-default">
      <xsl:call-template name="escape-text" mode="escape-html">
        <xsl:with-param name="input" select="concat($injected-title,language[@default='true']/@title)"/>
      </xsl:call-template>
    </xsl:variable>
          <dscr:jsondocument title="{$title-escaped-default}" hash="link-{generate-id(.)}">
            [
            <xsl:for-each select="language">
              <xsl:variable name="title-escaped">
                <xsl:call-template name="escape-text" mode="escape-html">
                  <xsl:with-param name="input" select="concat($injected-title,@title)"/>
                </xsl:call-template>
              </xsl:variable>
              {
                "lang": "<xsl:value-of select="@lang"/>",
                "default": <xsl:call-template name="determine-default"/>,
                "title": "<xsl:value-of select="$title-escaped"/>",
                "lang-switchable": true,
                "format": {
                <xsl:for-each select="url">
                  "<xsl:value-of select="@format"/>": "<xsl:value-of select="@href"/>",
                </xsl:for-each>
                },
                "date": false
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

  <xsl:template name="docset-title">
    <xsl:param name="node" select="."/>
    <!-- Finding out the correct product name is hard. FIXME: Is that logic
    quite right? It should be:
    docset/acronym > docset/name > product/acronym > product/name. -->
    <xsl:value-of
      select="(($node/ancestor::product/name|$node/ancestor::product/acronym)[last()]|
               ($node/ancestor::docset/name|$node/ancestor::docset/acronym)[last()])[last()]"/>
    <xsl:text> </xsl:text>
    <xsl:value-of select="$node/ancestor::docset/version"/>
  </xsl:template>

</xsl:stylesheet>
