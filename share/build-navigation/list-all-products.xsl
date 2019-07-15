<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet
[
]>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:exsl="http://exslt.org/common">
  <xsl:output method="text"/>

  <xsl:template match="@*|node()"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//docset"/>
  </xsl:template>

  <xsl:template match="docset">
    <xsl:value-of select="concat(ancestor::product/@productid,'/',@setid,'&#10;')"/>
  </xsl:template>

</xsl:stylesheet>
