<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<!-- Check that one docset is used as the default deocset, so we can do
referrals to it. -->


  <xsl:output method="text"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <xsl:variable name="default_docsets" select="count(//docset/@default[. = 'true' or . = '1'])"/>
    <xsl:choose>
      <xsl:when test="$default_docsets &lt; 1">
        <xsl:text>No docset has its default attribute set to "true" or "1". Each configuration file must have exactly 1 docset with this value.</xsl:text>
        <xsl:text>&#10;---&#10;</xsl:text>
      </xsl:when>
      <xsl:when test="$default_docsets &gt; 1">
        <xsl:value-of select="$default_docsets"/>
        <xsl:text> docsets have their default attribute set to "true" or "1". Each configuration file must have exactly 1 docset with this value.</xsl:text>
        <xsl:text>&#10;---&#10;</xsl:text>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
