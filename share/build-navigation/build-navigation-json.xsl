<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common"
  extension-element-prefixes="exsl"
  exclude-result-prefixes="exsl">

  <xsl:template match="/">
    <!-- Create a list of available products. -->
    <!-- FIXME: We need to cross-check this list against what is available in the cache to avoid showing products that aren't built yet (at least in the public version.) -->
    <exsl:document
     href="products.json"
     method="text"
     encoding="UTF-8"
     indent="no"
     media-type="application/x-json">
{
  "products": {
     <xsl:apply-templates select="//docset" mode="generate-product-list"/>
  }
}
<!--        "title": "example glossary",-->
    </exsl:document>

    <!-- Create individual JSON files for each docset -->
    <!--<exsl:document
     href="product-x.json"
     method="text"
     encoding="UTF-8"
     indent="no"
     media-type="application/x-json">
     flab!
    </exsl:document>-->
  </xsl:template>

  <!-- Make sure to exclude products based on lifecycle. -->
  <!-- Make sure to handle SBP differently. -->
  <xsl:template match="docset" mode="generate-product-list">
    "<xsl:value-of select="ancestor::product/@productid"/>/<xsl:value-of select="@setid"/>": {
      "productid": "<xsl:value-of select="ancestor::product/@productid"/>",
      "setid": "<xsl:value-of select="@setid"/>",
      "visible": <xsl:choose>
        <xsl:when test="@navigation-visible = 'hidden'">
          <xsl:text>false</xsl:text>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>true</xsl:text>
        </xsl:otherwise>
      </xsl:choose>,
      "productline": "<xsl:value-of select="ancestor::product/name"/>", <!-- not sure if productlines shouldn't be another section in the same json file -->
      "name": "<xsl:choose>
        <xsl:when test="name">
          <xsl:value-of select="name"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="ancestor::product/name"/>
        </xsl:otherwise>
      </xsl:choose>",
      "shortname": "<xsl:value-of select="ancestor::product/shortname"/>",
      "version": "<xsl:value-of select="version"/>",
      "defaultlanguage": "<xsl:value-of select="builddocs/language[@default='1' or @default='true']/@lang"/>",
      "languages": [<xsl:apply-templates select="builddocs/language[not(@default='1' or @default='true')]" mode="generate-product-list"/>
        ]
    }<xsl:if test="following-sibling::docset or parent::product/following-sibling::product/docset">,</xsl:if>
  </xsl:template>

  <xsl:template match="language" mode="generate-product-list">
           "<xsl:value-of select="@lang"/>"<xsl:if test="following-sibling::language">,</xsl:if></xsl:template>


</xsl:stylesheet>
