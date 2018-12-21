<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:date="http://exslt.org/dates-and-times"
  extension-element-prefixes="date"
  exclude-result-prefixes="date">
  <xsl:output method="html" omit-xml-declaration="yes"/>
  <!-- Destroys our *wonderfully* arranged buttons to select the document
  format by inserting spaces between them. -->
  <!--<xsl:output method="xml" indent="yes"/>-->



  <!-- PARAMETERS -->

  <xsl:param name="language" select="'en-us'"/>

  <xsl:param name="template_translation">
    <xsl:message terminate="yes">Translation file XSLT parameter missing.</xsl:message>
  </xsl:param>
  <xsl:param name="cache_file">
    <xsl:message terminate="yes">Stitched document cache file XSLT parameter missing.</xsl:message>
  </xsl:param>

  <xsl:param name="doc_language">
    <xsl:message terminate="yes">Document language XSLT parameter missing.</xsl:message>
  </xsl:param>
  <xsl:param name="ui_translation">
    <xsl:message terminate="yes">UI translation XSLT parameter missing.</xsl:message>
  </xsl:param>



  <!-- VARIABLES -->
  <xsl:variable name="translation_content" select="document($template_translation)/docservtranslation"/>
  <xsl:variable name="cache_content" select="document($cache_file)/docservcache"/>



  <!-- UTILITY TEMPLATES -->

  <xsl:template name="find-translation">
    <xsl:param name="name" select="''"/>

    <xsl:choose>
      <xsl:when test="$translation_content/locale[@lang = $language][1]/content[@name = $name][1]">
        <xsl:copy-of select="($translation_content/locale[@lang = $language][1]/content[@name = $name])[1]/node()[self::* or self::text()]"/>
      </xsl:when>
      <xsl:when test="$translation_content/locale[@default[. = '1' or . = 'true']][1]/content[@name = $name][1]">
        <xsl:copy-of select="$translation_content/locale[@default[. = '1' or . = 'true']][1]/content[@name = $name][1]/node()[self::* or self::text()]"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message>Requested translation string <xsl:value-of select="$name"/> does not exist.</xsl:message>
        <xsl:text>TRANSLATION STRING </xsl:text>
        <xsl:value-of select="$name"/>
        <xsl:text> MISSING.</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template name="find-document-name">
    <xsl:param name="productid" select="''"/>
    <xsl:param name="setid" select="''"/>
    <xsl:param name="dc" select="''"/>
    <xsl:param name="rootid" select="''"/>

    <xsl:choose>
      <xsl:when
        test="$rootid != '' and
              ($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[@rootid = $rootid])[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[@rootid = $rootid])[1]"/>
      </xsl:when>
      <xsl:when test="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[not(@rootid) or @rootid=''])[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[not(@rootid) or @rootid=''])[1]"/>
      </xsl:when>
      <xsl:when test="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title)[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title)[1]"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message>Requested cached title for <xsl:value-of select="concat($dc,'/',$rootid)"/> does not exist.</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template name="find-document-path">
    <xsl:param name="productid" select="''"/>
    <xsl:param name="setid" select="''"/>
    <xsl:param name="dc" select="''"/>
    <xsl:param name="rootid" select="''"/>
    <xsl:param name="format" select="''"/>

    <xsl:choose>
      <xsl:when
        test="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language][path[@format = $format]]/path)[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language][path[@format = $format]]/path)[1]"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message>Requested cached path for <xsl:value-of select="concat($dc,'/',$rootid)"/> does not exist.</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="*" priority="-1" mode="copy">
    <xsl:element name="{local-name(.)}">
      <xsl:apply-templates select="@*|*|text()"/>
    </xsl:element>
  </xsl:template>


  <xsl:template match="@*" priority="-1" mode="copy">
    <xsl:attribute name="{local-name(.)}">
      <xsl:value-of select="."/>
    </xsl:attribute>
  </xsl:template>


  <xsl:template match="text()" priority="-1" mode="copy">
    <xsl:value-of select="."/>
  </xsl:template>


  <!-- FLOW TEMPLATES -->

  <xsl:template match="/*">
    <div>
      <h1>
        <xsl:call-template name="find-translation">
          <xsl:with-param name="name" select="'pagehead'"/>
        </xsl:call-template>
      </h1>
      <xsl:call-template name="find-translation">
        <xsl:with-param name="name" select="'pagedesc'"/>
      </xsl:call-template>
      <xsl:if test="product">
        <ul class="docserv-product-overview">
          <xsl:apply-templates select="product">
            <xsl:sort
              lang="en"
              select="normalize-space(translate(name,
                'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))"/>
          </xsl:apply-templates>
        </ul>
      </xsl:if>
      <xsl:call-template name="find-translation">
        <xsl:with-param name="name" select="'pagebottom'"/>
      </xsl:call-template>
    </div>
  </xsl:template>


  <xsl:template match="product">
    <li id="list-{@productid}">
      <h3><xsl:value-of select="name"/></h3>
      <xsl:choose>
        <xsl:when test="desc[@lang = $doc_language]">
          <xsl:apply-templates select="desc[@lang = $doc_language]"/>
        </xsl:when>
        <xsl:when test="desc[@lang = $ui_language]">
          <xsl:apply-templates select="desc[@lang = $ui_language]"/>
        </xsl:when>
        <xsl:when test="desc[@default[. = '1' or . = 'true']]">
          <xsl:apply-templates select="desc[@default[. = '1' or . = 'true']]"/>
        </xsl:when>
      </xsl:choose>
      <ul>
        <xsl:apply-templates select="docset"/>
      </ul>
    </li>
  </xsl:template>


  <xsl:template match="desc">
    <xsl:apply-templates select="*|text()" mode="copy"/>
  </xsl:template>


  <xsl:template match="docset">
    <xsl:if test="$internal_mode = 1 or @lifecycle != 'unpublished'">
      <li id="list-{ancestor::*/@productid}-{@setid}">
        <h4><xsl:value-of select="version"/></h4>
        <xsl:choose>
          <xsl:when test="@lifecycle = 'beta'">
            <xsl:text> </xsl:text>
            <xsl:call-template name="find-translation">
              <xsl:with-param name="name" select="'internallabel'"/>
            </xsl:call-template>
          </xsl:when>
          <xsl:when test="@lifecycle = 'beta'">
            <xsl:text> </xsl:text>
            <xsl:call-template name="find-translation">
              <xsl:with-param name="name" select="'betalabel'"/>
            </xsl:call-template>
          </xsl:when>
        </xsl:choose>
        <ul class="doclist">
          <xsl:apply-templates select="builddocs/language[@lang = $doc_language]/deliverable|extralinks/link[not(@lang) or @lang = 'all' or @lang = $doc_language]"/>
        </ul>
      </li>
    </xsl:if>
  </xsl:template>


  <xsl:template match="deliverable[not(subdeliverable)]">
    <xsl:variable name="document_name_candidate">
      <xsl:call-template name="find-document-name">
        <xsl:with-param name="productid" select="ancestor::product/@productid"/>
        <xsl:with-param name="setid" select="ancestor::docset/@setid"/>
        <xsl:with-param name="dc" select="dc"/>
        <xsl:with-param name="rootid" select="''"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="document_name">
      <xsl:choose>
        <xsl:when test="string-length($document_name_candidate) &gt; 0">
          <xsl:value-of select="$document_name_candidate"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="dc"/>
          <xsl:if test="string-length(@rootid) &gt; 0">
            <xsl:value-of select="concat('/',@rootid)"/>
          </xsl:if>
          <xsl:if test="$internal_mode">
            <xsl:text> </xsl:text>
            <xsl:call-template name="find-translation">
              <xsl:with-param name="name" select="'missingtitlelabel'"/>
            </xsl:call-template>
          </xsl:if>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <li>
      <xsl:value-of select="$document_name"/>
      <xsl:apply-templates select="format/@*[. = 'true' or . = '1']"/>
    </li>
  </xsl:template>


  <xsl:template match="format/@*">
    <xsl:variable name="format" select="local-name()"/>
    <xsl:variable name="format_text">
      <xsl:call-template name="find-translation">
        <xsl:with-param name="name" select="$format"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="document_path">
      <xsl:call-template name="find-document-path">
        <xsl:with-param name="productid" select="ancestor::product/@productid"/>
        <xsl:with-param name="setid" select="ancestor::docset/@setid"/>
        <xsl:with-param name="dc" select="../preceding-sibling::dc"/>
        <xsl:with-param name="format" select="$format"/>
        <xsl:with-param name="rootid" select="''"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="string-length($document_path) &gt; 0">
        <a href="{$document_path}"><xsl:value-of select="$format_text"/></a>
      </xsl:when>
      <xsl:when test="$internal_mode = 1">
        <span>
          <xsl:value-of select="$format_text"/>
          <xsl:text> </xsl:text>
          <xsl:call-template name="find-translation">
            <xsl:with-param name="name" select="'brokenlinklabel'"/>
          </xsl:call-template>
        </span>
      </xsl:when>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="deliverable">
    <xsl:apply-templates select="subdeliverable"/>
  </xsl:template>


  <xsl:template match="subdeliverable">
    <xsl:variable name="document_name_candidate">
      <xsl:call-template name="find-document-name">
        <xsl:with-param name="productid" select="ancestor::product/@productid"/>
        <xsl:with-param name="setid" select="ancestor::docset/@setid"/>
        <xsl:with-param name="dc" select="preceding-sibling::dc"/>
        <xsl:with-param name="rootid" select="."/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="document_name">
      <xsl:choose>
        <xsl:when test="string-length($document_name_candidate) &gt; 0">
          <xsl:value-of select="$document_name_candidate"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="dc"/>
          <xsl:if test="string-length(@rootid) &gt; 0">
            <xsl:value-of select="concat('/',@rootid)"/>
          </xsl:if>
          <xsl:if test="$internal_mode">
            <xsl:text> </xsl:text>
            <xsl:call-template name="find-translation">
              <xsl:with-param name="name" select="'missingtitlelabel'"/>
            </xsl:call-template>
          </xsl:if>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <li>
      <xsl:value-of select="$document_name"/>
      <xsl:apply-templates select="preceding-sibling::format/@*[. = 'true' or . = '1']">
        <xsl:with-param name="rootid" select="."/>
      </xsl:apply-templates>
    </li>
  </xsl:template>


  <xsl:template match="format/@*">
    <xsl:param name="rootid" select="''"/>
    <xsl:variable name="format" select="local-name()"/>
    <xsl:variable name="format_text">
      <xsl:call-template name="find-translation">
        <xsl:with-param name="name" select="$format"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="document_path_candidate">
      <xsl:call-template name="find-document-path">
        <xsl:with-param name="productid" select="ancestor::product/@productid"/>
        <xsl:with-param name="setid" select="ancestor::docset/@setid"/>
        <xsl:with-param name="dc" select="../preceding-sibling::dc"/>
        <xsl:with-param name="format" select="$format"/>
        <xsl:with-param name="rootid" select="$rootid"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="document_path">
      <xsl:if test="string-length($document_path_candidate) &gt; 0">
        <xsl:value-of select="$document_path_candidate"/>
        <xsl:if test="string-length($rootid) &gt; 0 and ($format = 'html' or $format = 'single-html')">
          <xsl:text>/</xsl:text>
          <xsl:choose>
            <xsl:when test="$format = 'html'">
              <xsl:value-of select="$rootid"/>
              <xsl:text>.html</xsl:text>
            </xsl:when>
            <xsl:when test="$format = 'single-html'">
              <xsl:text>#</xsl:text>
              <xsl:value-of select="$rootid"/>
            </xsl:when>
          </xsl:choose>
        </xsl:if>
      </xsl:if>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="string-length($document_path) &gt; 0">
        <a href="{$document_path}"><xsl:value-of select="$format_text"/></a>
      </xsl:when>
      <xsl:when test="$internal_mode = 1">
        <span>
          <xsl:value-of select="$format_text"/>
          <xsl:text> </xsl:text>
          <xsl:call-template name="find-translation">
            <xsl:with-param name="name" select="'brokenlinklabel'"/>
          </xsl:call-template>
        </span>
      </xsl:when>
    </xsl:choose>

  </xsl:template>


  <xsl:template match="link">
    <li>
      <a href="{@href}"><xsl:value-of select="."/></a>
    </li>
  </xsl:template>

</xsl:stylesheet>
