<?xml version="1.0" encoding="UTF-8"?>
<!--

Stylesheet to convert Docserv's stitch XML file into a JSON structure

$ xsltproc homepage-data2json.xsl docserv-stitch-file.xml

-->

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common"
  xmlns:m="urn:suse-x:mapping"
  exclude-result-prefixes="exsl">
  <xsl:strip-space elements="*"/>
  <xsl:output method="text"/>

  <!-- ============================================= -->
  <xsl:param name="baseurl">https://documentation.suse.com</xsl:param>

  <!-- ============================================= -->
  <!-- Mapping from product name to icon name -->
  <map xmlns="urn:suse-x:mapping">
    <product name="alp">SUSE_ALP</product>
    <product name="sles">SUSE_generic</product>
    <product name="liberty">SUSE_Liberty_Linux</product>
    <product name="sle-ha">SLE_HAE</product>
  </map>
  <xsl:variable name="mapnodes" select="document('')/*/m:map/*"/>


  <!-- ============================================= -->
  <xsl:template match="/*">
    <xsl:message terminate="yes">
      <xsl:text>ERROR: Expected the tag 'positivedocservconfig'.&#10;</xsl:text>
      <xsl:text>The stitch file contains the root element </xsl:text>
      <xsl:value-of select="concat('&lt;', local-name(.), '>')"/>
    </xsl:message>
  </xsl:template>

  <xsl:template match="/positivedocservconfig/hashes"/>

  <xsl:template match="/positivedocservconfig | /docservconfig">
    <xsl:text>{</xsl:text>
    <!--
     "page_title": "Jinja template",
     "greeting": "Hello 3G!",
     "topic_template": "Index Page",
     "topic_description": "Lorem ipsum...",
    -->
    <xsl:text>  "productsList": [&#10;</xsl:text>
    <xsl:apply-templates/>
    <xsl:text>  ]</xsl:text>
    <xsl:text>}</xsl:text>
  </xsl:template>

  <xsl:template match="product">
    <xsl:variable name="name" select="@productid"/>
    <xsl:variable name="icon" select="$mapnodes[@name=$name]"/>
    <xsl:variable name="title">
      <xsl:choose>
        <xsl:when test="desc/title">
          <xsl:value-of select="normalize-space(desc/title)"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="normalize-space(desc/p[1])"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:text> {</xsl:text>
    "label": <xsl:value-of select="concat('&quot;', name, '&quot;')"/>,
    "urlParam": <xsl:value-of select="concat('&quot;/', @productid, '/&quot;')"/>,
    "icon": <xsl:value-of select="concat('&quot;', $icon, '&quot;')"/>,
    "type": "product",
    "description": <xsl:value-of select="concat('&quot;', substring($title, 1, 79), '…&quot;')"/>,
    "versions": [
        <xsl:apply-templates select="docset"/>
    ]
    <xsl:text> }</xsl:text>
    <xsl:if test=" following-sibling::product">,&#10;</xsl:if>
  </xsl:template>

  <xsl:template match="docset">
    <xsl:variable name="productname">
      <xsl:choose>
        <xsl:when test="name">
          <xsl:value-of select="normalize-space(name)"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="normalize-space(../name)"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="urlparam" select="concat('/', parent::*/@productid, '/', @setid)"/>
    <xsl:text>  {</xsl:text>
    "label": <xsl:value-of select="concat('&quot;', ../name, '&quot;')"/>,
    "urlParam": <xsl:value-of select="concat('&quot;', $urlparam, '/&quot;')"/>,
    "productParam": <xsl:value-of select="concat('&quot;', parent::*/@productid, '/&quot;')"/>,
    "productName": <xsl:value-of select="concat('&quot;', $productname, '&quot;')"/>,
    "pointingUrl": <xsl:value-of select="concat('&quot;', $baseurl, $urlparam, '/&quot;')"/>
    <xsl:text>  }</xsl:text>
    <xsl:if test=" following-sibling::docset">,&#10;        </xsl:if>
  </xsl:template>

</xsl:stylesheet>