<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:dscr="https://github.com/openSUSE/docserv/docserv2_cache_result"
  exclude-result-prefixes="dscr">

  <xsl:variable name="cache_content" select="document($cache_file)/docservcache"/>

  <xsl:template name="cache-request">
    <!-- supported values: 'hash' & 'title' -->
    <xsl:param name="information" select="''"/>

    <xsl:param name="productid" select="ancestor::product/@productid"/>
    <xsl:param name="setid" select="ancestor::docset/@setid"/>
    <xsl:param name="doc_language" select="ancestor::language/@lang"/>
    <xsl:param name="dc">
      <xsl:choose>
        <xsl:when test="self::deliverable">
          <xsl:value-of select="dc"/>
        </xsl:when>
        <xsl:when test="self::subdeliverable">
          <xsl:value-of select="preceding-sibling::dc"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:message terminate="yes">Error: cache-request is not in a deliverable or subdeliverable. This should never happen.</xsl:message>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:param>
    <xsl:param name="rootid">
      <xsl:choose>
        <xsl:when test="self::deliverable"/>
        <xsl:when test="self::subdeliverable">
          <xsl:value-of select="."/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:message terminate="yes">Error: cache-request is not in a deliverable or subdeliverable. This should never happen.</xsl:message>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:param>

    <xsl:variable name="result">
      <xsl:choose>
        <xsl:when test="$information = 'hash'">
          <xsl:call-template name="get-hash">
            <xsl:with-param name="productid" select="$productid"/>
            <xsl:with-param name="setid" select="$setid"/>
            <xsl:with-param name="doc_language" select="$doc_language"/>
            <xsl:with-param name="dc" select="$dc"/>
            <xsl:with-param name="rootid" select="$rootid"/>
          </xsl:call-template>
        </xsl:when>
        <xsl:when test="$information = 'title'">
          <xsl:call-template name="get-title">
            <xsl:with-param name="productid" select="$productid"/>
            <xsl:with-param name="setid" select="$setid"/>
            <xsl:with-param name="doc_language" select="$doc_language"/>
            <xsl:with-param name="dc" select="$dc"/>
            <xsl:with-param name="rootid" select="$rootid"/>
          </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
          <xsl:message terminate="yes">Error: cache-request run without valid $information parameter.</xsl:message>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:choose>
      <xsl:when test="$result != ''">
        <xsl:value-of select="$result"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message>Requested cached <xsl:value-of select="$information"/> for <xsl:value-of select="concat($dc,'/',$rootid)"/> does not exist.</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template name="get-hash">
    <xsl:param name="productid" select="''"/>
    <xsl:param name="setid" select="''"/>
    <xsl:param name="doc_language" select="''"/>
    <xsl:param name="dc" select="''"/>
    <xsl:param name="rootid" select="''"/>

    <xsl:choose>
      <xsl:when
        test="$rootid != '' and
              ($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[@rootid = $rootid]/@hash)[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[@rootid = $rootid]/@hash)[1]"/>
      </xsl:when>
      <xsl:when test="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[not(@rootid) or @rootid='']/@hash)[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title[not(@rootid) or @rootid='']/@hash)[1]"/>
      </xsl:when>
      <xsl:when test="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title/@hash)[1]">
        <xsl:value-of select="($cache_content/document[@productid = $productid][@setid = $setid][@dc = $dc][@lang = $doc_language]/title/@hash)[1]"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

  <xsl:template name="get-title">
    <xsl:param name="productid" select="''"/>
    <xsl:param name="setid" select="''"/>
    <xsl:param name="doc_language" select="''"/>
    <xsl:param name="dc" select="''"/>
    <xsl:param name="rootid" select="''"/>

    <xsl:variable name="title">
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
      </xsl:choose>
    </xsl:variable>

    <xsl:value-of select="normalize-space(translate($title, '&#10;', ''))"/>
  </xsl:template>



  <xsl:template name="cache-hash-match">
    <xsl:param name="hash" select="''"/>

    <dscr:cacheresult>
     <xsl:for-each select="$cache_content/descendant::title[@hash = $hash]">
       <xsl:variable name="format" select="ancestor::document/path/@format"/>
       <xsl:variable name="rootdoc">
         <xsl:choose>
           <xsl:when test="@rootid and @rootid != ''"><xsl:value-of select="@rootid"/></xsl:when>
           <xsl:otherwise>index</xsl:otherwise>
         </xsl:choose>
       </xsl:variable>
       <xsl:variable name="path">
         <xsl:choose>
           <xsl:when test="$format = 'html' or $format = 'single-html'">
             <xsl:value-of select="concat(ancestor::document/path,$rootdoc,'.html')"/>
           </xsl:when>
           <xsl:otherwise>
             <xsl:value-of select="ancestor::document/path"/>
           </xsl:otherwise>
         </xsl:choose>
       </xsl:variable>

       <dscr:result
         dc="{ancestor::document/@dc}"
         rootid="{@rootid}"
         format="{ancestor::document/path/@format}"
         path="{$path}"
         lang="{ancestor::document/@lang}"
         productid="{ancestor::document/@productid}"
         setid="{ancestor::document/@setid}"
         title="{.}"/>
     </xsl:for-each>
    </dscr:cacheresult>
  </xsl:template>


</xsl:stylesheet>
