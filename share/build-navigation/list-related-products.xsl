<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet
[
]>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common">
  <xsl:output method="text"/>

  <xsl:param name="product">
    <xsl:message terminate="yes">Need a valid $product XSLT parameter to find related docsets.</xsl:message>
  </xsl:param>
  <xsl:param name="docset">
    <xsl:message terminate="yes">Need a valid $docset XSLT parameter to find related docsets.</xsl:message>
  </xsl:param>
  <xsl:param name="internal-mode" select="'false'"/>

  <xsl:template match="@*|node()"/>

  <xsl:template match="/">
    <xsl:if test="not(//product[@productid = $product])">
      <xsl:message terminate="yes">Product ID from $product XSLT parameter ("<xsl:value-of select="$product"/>") does not exist.</xsl:message>
    </xsl:if>
    <xsl:if test="not(//product[@productid = $product]/docset[@setid = $docset])">
      <xsl:message terminate="yes">
        <xsl:text>Docset ID from XSLT parameter $docset ("</xsl:text>
        <xsl:value-of select="$docset"/>
        <xsl:text>") does not exist within $product ("</xsl:text>
        <xsl:value-of select="$product"/>
        <xsl:text>").</xsl:text>
      </xsl:message>
    </xsl:if>

    <xsl:choose>
      <xsl:when test="$internal-mode = 'true'">
        <xsl:apply-templates select="//docset/internal/ref"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="//docset[not(@lifecycle = 'unpublished')]/internal/ref"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="ref">
    <xsl:if test="@product = $product and @docset = $docset">
      <xsl:value-of select="concat(ancestor::product/@productid, '/', ancestor::docset/@setid, '&#10;')"/>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
