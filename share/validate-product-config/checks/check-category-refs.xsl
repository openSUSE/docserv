<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<!-- make sure that all references to category ids actually reference an
existing category. -->
<!-- FIXME: we're currently not checking for the same category used twice, e.g.:
@category="category1 category2 category1" -->


  <xsl:output method="text"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//@category"/>
  </xsl:template>

  <xsl:template match="@category">
    <xsl:call-template name="catvalid"/>
  </xsl:template>

  <xsl:template name="catvalid">
    <xsl:param name="string" select="concat(.,' ')"/>
    <xsl:if test="not(//@categoryid = substring-before($string, ' '))">
      <xsl:text>Referenced category "</xsl:text>
      <xsl:value-of select="substring-before($string, ' ')"/>
      <xsl:text>" does not exist. The following categories are valid in this configuration file:&#10;</xsl:text>
      <xsl:apply-templates select="//category/@categoryid"/>
      <xsl:text>&#10;---&#10;</xsl:text>
    </xsl:if>
    <xsl:if test="string-length(substring-after($string, ' ')) &gt; 0">
      <xsl:call-template name="catvalid">
        <xsl:with-param name="string" select="substring-after($string, ' ')"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <xsl:template match="@categoryid">
    <xsl:value-of select="."/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

</xsl:stylesheet>
