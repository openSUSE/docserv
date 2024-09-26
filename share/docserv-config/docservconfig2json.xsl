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

  <!-- ====== Parameters ====== -->
  <!-- Should the desc/title tag be suppressed from the output? -->
  <xsl:param name="suppress-desc-title" select="true()"/>

  <!-- Use the following separator for all tags inside <desc> -->
  <xsl:param name="tag-sep"><xsl:text>\n</xsl:text></xsl:param>

  <!-- Use this separator to separate multiple docsets in stdout.
    Only used when you set infile=false().
  -->
  <xsl:param name="docset-sep">
    <xsl:text>&#10;&#10;====&#10;&#10;</xsl:text>
  </xsl:param>

  <!-- Which lifecycle we search for? -->
  <xsl:param name="lifecycle">supported</xsl:param>

  <!-- The product and docset to select.
    If they are empty, all products or docsets are processed -->
  <xsl:param name="product"/>
  <xsl:param name="docset"/>

  <!-- Use output directory to store JSON files.
    Always add a trailing "/"!! -->
  <xsl:param name="outputdir"><xsl:text>./</xsl:text></xsl:param>

  <!-- Should the JSON be stored or printed on stdout?
    true() = store them in a file
    false() = print them to stdout; also use docset-sep if needed.
  -->
  <xsl:param name="infile" select="true()"/>


  <!-- ====== Templates ====== -->
  <xsl:template match="/">
    <xsl:variable name="rootproduct" select="(product|*/product)"/>
    <xsl:choose>
      <xsl:when test="$product != '' and $docset != ''">
        <xsl:variable name="product-node" select="$rootproduct[@productid=$product][docset[@setid=$docset]]"/>
        <xsl:message>INFO: Selected product=<xsl:value-of select="concat('&quot;', $product, '&quot;')"/> and docset=<xsl:value-of select="concat('&quot;', $docset, '&quot;')"/>
INFO: Found <xsl:value-of select="count($product-node)"/> node.</xsl:message>
        <xsl:apply-templates select="$product-node"/>
      </xsl:when>
      <xsl:when test="$product != ''">
        <xsl:variable name="product-node" select="$rootproduct[@productid=$product]"/>
        <xsl:message>INFO: Selected product=<xsl:value-of select="concat('&quot;', $product, '&quot;')"/>.
Found <xsl:value-of select="count($product-node)"/> node
        </xsl:message>
        <xsl:apply-templates select="$product-node"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="*"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="*/product">
    <xsl:call-template name="process-product" />
  </xsl:template>

  <xsl:template match="/product" name="process-product">
    <xsl:variable name="name">
      <xsl:apply-templates select="name"/>
    </xsl:variable>
    <xsl:variable name="productid">
      <xsl:apply-templates select="@productid"/>
    </xsl:variable>

    <xsl:message>INFO: Processing product <xsl:value-of select="concat('&quot;', @productid, '&quot;')"/></xsl:message>
    <xsl:choose>
      <xsl:when test="$lifecycle != '' and $docset != ''">
        <xsl:apply-templates select="docset[@lifecycle=$lifecycle][@setid=$docset]" >
          <xsl:with-param name="name" select="$name"/>
          <xsl:with-param name="productid" select="$productid"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:when test="$lifecycle != '' and $docset = ''">
        <xsl:apply-templates select="docset[@lifecycle=$lifecycle]" >
          <xsl:with-param name="name" select="$name"/>
          <xsl:with-param name="productid" select="$productid"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:when test="$lifecycle = '' and $docset != ''">
        <xsl:apply-templates select="docset[@setid=$docset]" >
          <xsl:with-param name="name" select="$name"/>
          <xsl:with-param name="productid" select="$productid"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="docset" >
          <xsl:with-param name="name" select="$name"/>
          <xsl:with-param name="productid" select="$productid"/>
        </xsl:apply-templates>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Ignored elements -->
  <xsl:template match="hashes|product"/>


  <xsl:template match="docset">
    <xsl:param name="name"/>
    <xsl:param name="productid"/>
    <xsl:variable name="productid-attr" select="../@productid" />
    <xsl:variable name="filename" select="concat($outputdir, $productid-attr, '/', @setid, '.json')"/>
    <xsl:variable name="content">
      <xsl:text>{&#10;</xsl:text>
      <xsl:value-of select="$name" />
      <xsl:value-of select="$productid" />
      <xsl:apply-templates select="@setid" />
      <xsl:apply-templates select="@lifecycle"/>
      <xsl:text>  "hide-productname": false,&#10;</xsl:text>
      <xsl:text>  "descriptions": [&#10;</xsl:text>
      <xsl:apply-templates select="../desc">
        <xsl:with-param name="docset" select="."/>
      </xsl:apply-templates>
      <xsl:text>  ],&#10;</xsl:text>
      <xsl:text>  "documents": [</xsl:text>
      <xsl:apply-templates select="builddocs/language[@default='1' or @default='true']" />
      <xsl:text>  ],&#10;</xsl:text>
      <xsl:text>  "archives": []&#10;</xsl:text>
      <xsl:text>}</xsl:text>
    </xsl:variable>

    <xsl:choose>
      <xsl:when test="$infile">
        <exsl:document
          href="{$filename}"
          method="text" encoding="UTF-8" indent="no"
          media-type="application/x-json">
          <xsl:value-of select="$content"/>
        </exsl:document>
        <xsl:message>Wrote <xsl:value-of select="$filename"/></xsl:message>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$content"/>
      </xsl:otherwise>
    </xsl:choose>
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
    <xsl:variable name="this-lang" select="@lang"/>
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
      <xsl:apply-templates select="($docset/overridedesc/desc[1]|
                                    $docset/overridedesc/desc[@lang = $this-lang]
                                    )[last()]" mode="desc">
        <xsl:with-param name="lang" select="$this-lang"/>
      </xsl:apply-templates>
    </xsl:variable>
    <xsl:text>    {&#10;</xsl:text>
    <xsl:text>       "lang": </xsl:text>
    <xsl:value-of select="concat('&quot;', @lang, '&quot;,&#10;')"/>
    <xsl:text>       "default": </xsl:text>
    <xsl:value-of select="concat($default, ',&#10;')"/>
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
    <xsl:value-of select="concat('&lt;/', name($node), '>', $tag-sep)"/>
  </xsl:template>

  <xsl:template match="title" mode="desc">
    <xsl:param name="lang"/>
    <xsl:param name="node" select="."/>
    <xsl:if test="not($suppress-desc-title)">
      <xsl:text>&lt;div class=\"title\"></xsl:text>
      <xsl:apply-templates mode="desc">
        <xsl:with-param name="lang" select="$lang"/>
      </xsl:apply-templates>
      <xsl:text>&lt;/div></xsl:text>
    </xsl:if>
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


  <xsl:template match="language">
    <xsl:message>Ignoring language/@lang=<xsl:value-of select="@lang"/></xsl:message>
  </xsl:template>

  <xsl:template match="language[@default='1' or @default='true']">
    <xsl:message>  Found <xsl:value-of
      select="count(deliverable)"/> deliverable(s)</xsl:message>
    <xsl:apply-templates select="deliverable"/>
  </xsl:template>


  <xsl:template name="process-dc">
    <xsl:param name="node" select="."/>
    <xsl:param name="thisdc"/>
    <xsl:param name="default">
      <xsl:choose>
        <xsl:when test="$node/../@default = '1' or $node/../@default = 'true'">true</xsl:when>
        <xsl:otherwise>false</xsl:otherwise>
      </xsl:choose>
    </xsl:param>
    <xsl:param name="lang" select="$node/../@lang"/>
    <xsl:param name="dc" select="$node/dc"/>

    <xsl:text>    {&#10;</xsl:text>
    <xsl:text>      "lang": </xsl:text>
    <xsl:value-of select="concat('&quot;', $lang, '&quot;,&#10;')"/>
    <xsl:text>      "default": </xsl:text>
    <xsl:value-of select="concat($default, ',&#10;')"/>
    <xsl:text>      "title": "",&#10;</xsl:text>
    <xsl:text>      "subtitle": "",&#10;</xsl:text>
    <xsl:text>      "description": "",&#10;</xsl:text>
    <xsl:text>      "dcfile": </xsl:text>
    <xsl:value-of select="concat('&quot;', $dc, '&quot;,&#10;')" />
    <xsl:text>      "format": {</xsl:text>
    <!-- We need to use the format from the orginal, English dc file -->
    <xsl:apply-templates select="$thisdc/ancestor-or-self::deliverable/format" />
    <xsl:text>},&#10;</xsl:text>
    <xsl:text>      "dateModified": ""&#10;</xsl:text>
    <xsl:text>    }</xsl:text>
  </xsl:template>


  <xsl:template match="deliverable">
    <xsl:apply-templates select="dc"/>
  </xsl:template>

  <xsl:template match="deliverable/dc">
    <xsl:variable name="thisdc" select="."/>
    <!-- How likely is it that we get more than one @lang node-sets? -->
    <xsl:variable name="lang" select="(ancestor::*/@lang)[last()]"/>
    <xsl:variable name="other-delis"
      select="ancestor::builddocs/language[not(@default='1')]/deliverable[dc[. = $thisdc]]"/>

    <xsl:text>    {&#10;</xsl:text>
    <xsl:text>      "docs": [&#10;</xsl:text>
    <xsl:call-template name="process-dc">
      <xsl:with-param name="node" select=".."/>
      <xsl:with-param name="thisdc" select="$thisdc"/>
    </xsl:call-template>
    <!-- If we find the same DC file for other languages, process them in the
         same entry
    -->
    <xsl:if test="$other-delis">
      <xsl:text>,&#10;</xsl:text>
      <xsl:message>  Found languages for <xsl:value-of select="$thisdc"/>: <xsl:for-each select="$other-delis"><xsl:value-of select="current()/../@lang"/>, </xsl:for-each></xsl:message>
      <xsl:for-each select="$other-delis">
        <xsl:variable name="node" select="current()"/>
        <xsl:call-template name="process-dc">
          <xsl:with-param name="node" select="$node"/>
          <xsl:with-param name="thisdc" select="$thisdc"/>
        </xsl:call-template>
        <xsl:if test="position() != last()">,&#10;</xsl:if>
      </xsl:for-each>
    </xsl:if>
    <xsl:text>      ],&#10;</xsl:text>

    <xsl:text>      "tasks": [],&#10;</xsl:text>
    <xsl:text>      "products": [],&#10;</xsl:text>
    <xsl:text>      "docTypes": [],&#10;</xsl:text>
    <xsl:text>      "isGated": false,&#10;</xsl:text>
    <xsl:text>      "rank": ""&#10;</xsl:text>
    <xsl:text>    }</xsl:text>
    <xsl:if test="ancestor::deliverable/following-sibling::deliverable">
      <xsl:text>,&#10;</xsl:text>
    </xsl:if>
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