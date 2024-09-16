<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet
[
  <!ENTITY sortlower "abcdefghijklmnopqrstuvwxyz">
  <!ENTITY sortupper "ABCDEFGHIJKLMNOPQRSTUVWXYZ">
]>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common"
  extension-element-prefixes="exsl"
  exclude-result-prefixes="exsl">

  <xsl:output method="text"/>
  <xsl:strip-space elements="*"/>

  <!-- Parameters -->
  <xsl:param name="add-empty-docs" select="true()" />


  <xsl:template name="process-docset">
    <xsl:param name="nodes" select="."/>

    <xsl:for-each select="$nodes">
      <xsl:if test="@lifecycle = 'supported'">
        <xsl:apply-templates select=".">
          <xsl:with-param name="pos" select="position()"/>
          <xsl:with-param name="last" select="last()"/>
        </xsl:apply-templates>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>


  <xsl:template match="/docservconfig|/positivedocservconfig">
    <xsl:text>[&#10;</xsl:text>
    <xsl:call-template name="process-docset">
      <xsl:with-param name="nodes" select="product/docset" />
    </xsl:call-template>
    <xsl:text>]&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="/product">
    <xsl:call-template name="process-docset">
      <xsl:with-param name="nodes" select="docset" />
    </xsl:call-template>
  </xsl:template>

  <!-- Ignored elements -->
  <xsl:template match="hashes|product"/>


  <xsl:template match="docset">
    <xsl:param name="pos" select="0"/>
    <xsl:param name="last" select="0"/>
    <xsl:variable name="product" select="parent::product"/>
    <xsl:variable name="name" select="$product/name"/>
    <xsl:variable name="next-product" select="count(parent::product/following-sibling::product)"/>

    <xsl:text>  {&#10;</xsl:text>
    <xsl:apply-templates select="$name"/>
    <xsl:apply-templates select="$product/@productid"/>
    <xsl:apply-templates select="@setid"/>
    <xsl:apply-templates select="@lifecycle"/>

    <xsl:text>  "descriptions": [&#10;</xsl:text>
    <xsl:apply-templates select="$product/desc">
      <xsl:with-param name="docset" select="."/>
    </xsl:apply-templates>
    <xsl:text>  ],&#10;</xsl:text>

    <xsl:text>  "documents": [</xsl:text>
    <!-- This needs to be filled from daps metadata and docserv config -->
    <xsl:if test="$add-empty-docs">
      <xsl:text>    {&#10;</xsl:text>
      <xsl:text>       "docs": [&#10;</xsl:text>
      <xsl:for-each select="builddocs/language/deliverable">
        <xsl:apply-templates select=".">
          <xsl:with-param name="pos" select="position()"/>
          <xsl:with-param name="last" select="last()"/>
        </xsl:apply-templates>
      </xsl:for-each>
      <xsl:text>       ],&#10;</xsl:text>
      <xsl:text>       "tasks": [],&#10;</xsl:text>
      <xsl:text>       "products": [],&#10;</xsl:text>
      <xsl:text>       "docTypes": [],&#10;</xsl:text>
      <xsl:text>       "isGated": false,&#10;</xsl:text>
      <xsl:text>       "rank": "2"&#10;</xsl:text>
      <xsl:text>    }&#10;</xsl:text>
    </xsl:if>
    <xsl:text>  ],&#10;</xsl:text>

    <xsl:text>  "archives": [</xsl:text>
    <!-- TODO -->
    <xsl:text>  ]&#10;</xsl:text>
    <xsl:text>  }</xsl:text>
    <xsl:message>
    pos=<xsl:value-of select="$pos"/>, last=<xsl:value-of select="$last"/> => <xsl:value-of select="$pos != $last"/>
    next-product=<xsl:value-of select="$next-product"/>
    </xsl:message>
    <xsl:choose>
      <xsl:when test="$next-product = 0"/>
      <xsl:when test="$pos &lt; $last">,</xsl:when>
      <xsl:otherwise/>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="product/name">
    <xsl:text>  "productname": </xsl:text>
    <xsl:value-of select="concat('&quot;', normalize-space(.), '&quot;,&#10;')"/>
  </xsl:template>

  <xsl:template match="product/@productid">
    <xsl:text>  "acronym": </xsl:text>
    <xsl:value-of select="concat('&quot;', normalize-space(.), '&quot;,&#10;')"/>
  </xsl:template>

  <xsl:template match="docset/@setid">
    <xsl:text>  "version": </xsl:text>
    <xsl:value-of select="concat('&quot;', normalize-space(.), '&quot;,&#10;')"/>
  </xsl:template>

  <xsl:template match="docset/@lifecycle">
    <xsl:param name="node" select="."/>
    <xsl:text>  "lifecycle": </xsl:text>
    <xsl:value-of select="concat('&quot;', normalize-space(.), '&quot;,&#10;')"/>
  </xsl:template>

  <xsl:template match="product/desc">
    <xsl:param name="docset"/>
    <xsl:variable name="default">
      <xsl:choose>
        <xsl:when test="@default = '1' or @default = 'true'">true</xsl:when>
        <xsl:otherwise>false</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="content">
      <xsl:apply-templates mode="desc">
        <xsl:with-param name="lang" select="@lang"/>
      </xsl:apply-templates>
    </xsl:variable>
    <xsl:variable name="docset-desc">
      <xsl:apply-templates select="$docset/overridedesc" mode="desc">
        <xsl:with-param name="lang" select="@lang"/>
      </xsl:apply-templates>
    </xsl:variable>
    <xsl:text>    {&#10;</xsl:text>
    <xsl:text>       "lang": </xsl:text>
    <xsl:value-of select="concat('&quot;', @lang, '&quot;,&#10;')"/>
    <xsl:text>       "default": </xsl:text>
    <xsl:value-of select="concat('&quot;', $default, '&quot;,&#10;')"/>
    <xsl:text>       "description": "</xsl:text>
    <xsl:choose>
      <xsl:when test="$docset/overridedesc/@treatment = 'append'">
        <xsl:value-of select="normalize-space($content)"/>
        <xsl:value-of select="normalize-space($docset-desc)"/>
      </xsl:when>
      <xsl:when test="$docset/overridedesc/@treatment = 'prepend'">
        <xsl:value-of select="normalize-space($docset-desc)"/>
        <xsl:value-of select="normalize-space($content)"/>
      </xsl:when>
      <xsl:when test="$docset/overridedesc/@treatment = 'replace'">
        <xsl:value-of select="normalize-space($docset-desc)"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="normalize-space($content)"/>
      </xsl:otherwise>
    </xsl:choose>

    <xsl:text>"&#10;</xsl:text>
    <xsl:text>    }</xsl:text>
    <xsl:if test="following-sibling::desc">,</xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <xsl:template match="overridedesc" mode="desc">
    <xsl:param name="lang"/>
      <xsl:apply-templates mode="desc">
        <xsl:with-param name="lang" select="$lang"/>
      </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="desc" mode="desc">
    <xsl:param name="lang"/>
    <xsl:if test="@lang = $lang">
      <xsl:apply-templates mode="desc">
        <xsl:with-param name="lang" select="$lang"/>
      </xsl:apply-templates>
    </xsl:if>
  </xsl:template>

  <xsl:template name="serialize-attributes">
    <xsl:param name="node" select="."/>
    <xsl:for-each select="$node/@*">
      <xsl:value-of select="concat(' ', name(), '=')"/>
      <xsl:text>\"</xsl:text>
      <xsl:value-of select="."/>
      <xsl:text>\"</xsl:text>
<!--      <xsl:if test="position() &lt; last()"><xsl:text> </xsl:text></xsl:if>-->
    </xsl:for-each>
  </xsl:template>

  <!-- Template to escape quotes in text nodes -->
  <xsl:template name="escape-quotes">
    <xsl:param name="text"/>
    <xsl:choose>
      <!-- If there is no quote in the text, return the text as is -->
      <xsl:when test="not(contains($text, '&quot;'))">
        <xsl:value-of select="$text"/>
      </xsl:when>
      <!-- If a quote is found, replace it with \" and recursively process the remaining text -->
      <xsl:otherwise>
        <xsl:value-of select="substring-before($text, '&quot;')"/>
        <xsl:text>\&quot;</xsl:text>
        <xsl:call-template name="escape-quotes">
          <xsl:with-param name="text" select="substring-after($text, '&quot;')"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Template to serialize HTML elements recursively -->
  <xsl:template match="*" mode="desc">
    <xsl:param name="lang"/>
    <xsl:param name="node" select="."/>

    <!-- Process the current element -->
    <xsl:value-of select="concat('&lt;', name($node))"/>

    <!-- Apply templates to handle attributes -->
    <xsl:apply-templates select="$node/@*" mode="desc"/>
    <xsl:text>&gt;</xsl:text>

    <!-- Process child nodes recursively -->
    <xsl:apply-templates mode="desc">
      <xsl:with-param name="lang" select="$lang"/>
    </xsl:apply-templates>

    <!-- Close the current element -->
    <xsl:value-of select="concat('&lt;/', name($node), '>\n')"/>
  </xsl:template>

  <!-- Template to handle attributes in 'desc' context -->
  <xsl:template match="@*" mode="desc">
    <xsl:text> </xsl:text>
    <xsl:value-of select="name()"/>
    <xsl:text>=\"</xsl:text>
    <xsl:value-of select="."/>
    <xsl:text>\"</xsl:text>
  </xsl:template>

  <!-- Template to handle text nodes in 'desc' context -->
  <xsl:template match="text()" mode="desc">
    <xsl:call-template name="escape-quotes">
      <xsl:with-param name="text" select="normalize-space()"/>
    </xsl:call-template>
  </xsl:template>


  <xsl:template match="language"><!-- [@default='1' or @default='true'] -->
    <xsl:param name="pos" select="0"/>
    <xsl:param name="last" select="0"/>
    <xsl:message>Found language</xsl:message>
    <xsl:apply-templates select="deliverable" />
    <xsl:if test="$pos != $last">,</xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="deliverable">
    <xsl:param name="pos" select="0" />
    <xsl:param name="last" select="0" />
    <xsl:variable name="thisdc" select="dc"/>
    <xsl:variable name="parent" select="parent::*[1]"/>
    <xsl:variable name="default">
      <xsl:choose>
        <xsl:when test="../@default = '1' or ../@default = 'true'">true</xsl:when>
        <xsl:otherwise>false</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="lang" select="../@lang"/>

    <xsl:text>    {&#10;</xsl:text>
    <xsl:text>      "lang": </xsl:text>
    <xsl:value-of select="concat('&quot;', $lang, '&quot;,&#10;')"/>
    <xsl:text>      "default": </xsl:text>
    <xsl:value-of select="concat($default, ',&#10;')"/>
    <xsl:text>      "title": "",&#10;</xsl:text>
    <xsl:text>      "subtitle": "",&#10;</xsl:text>
    <xsl:text>      "description": "",&#10;</xsl:text>
    <xsl:text>      "dcfile": </xsl:text>
    <xsl:value-of select="concat('&quot;', dc, '&quot;,&#10;')" />
    <xsl:text>      "formats": {</xsl:text>
    <xsl:choose>
      <xsl:when test="format">
        <xsl:apply-templates select="format" />
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="parent::*/parent::*/language[@default='1']/deliverable[dc=$thisdc]/format" />
      </xsl:otherwise>
    </xsl:choose>

    <xsl:text>},&#10;</xsl:text>
    <xsl:text>      "dateModified": ""&#10;</xsl:text>
    <xsl:text>    }</xsl:text>
    <xsl:if test="$pos != $last">,</xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="format">
    <xsl:for-each select="@*[. = '1' or . = 'true']">
       <xsl:value-of select="concat('&quot;', name(.), '&quot;: &quot;&quot;')"/>
       <xsl:if test="position() != last()">
          <xsl:text>, </xsl:text>
       </xsl:if>
  </xsl:for-each>
  </xsl:template>
</xsl:stylesheet>