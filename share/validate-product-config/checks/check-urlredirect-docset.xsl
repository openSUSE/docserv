<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<!-- Check that one docset is used as the default docset, so we can do
referrals to it. -->


  <xsl:output method="text"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//urlredirect/@docset"/>
  </xsl:template>

  <xsl:template match="urlredirect/@docset">
    <xsl:if test="not(. = //docset/@setid)">
      <xsl:text>Docset "</xsl:text>
      <xsl:value-of select="."/>
      <xsl:text>" referenced in urlredirect element does not exist.</xsl:text>
      <xsl:text>&#10;---&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
