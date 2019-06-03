<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<!-- make sure that all references to category ids actually reference an
existing category. -->

  <xsl:output method="text"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//@category"/>
  </xsl:template>

  <xsl:template match="@category">
    <xsl:if test="not(//@categoryid = .)">
      <xsl:text>Referenced category "</xsl:text>
      <xsl:value-of select="."/>
      <xsl:text>" does not exist.&#10;---&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
