<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xh="http://www.w3.org/1999/xhtml"
  xmlns:f="https://github.com/openSUSE/docserv/fragment"
  xmlns:l="https://github.com/openSUSE/docserv/l10n"
  exclude-result-prefixes="f l xh">
  <xsl:output method="html" omit-xml-declaration="yes" encoding="UTF-8" indent="yes"/>

  <xsl:param name="l10n-file">
    <xsl:message terminate="yes">Provide a path to a localization file via the parameter $l10n-file.</xsl:message>
  </xsl:param>

  <xsl:param name="fallback-l10n-file">
    <xsl:message terminate="yes">Provide a path to a fallback localization file via the parameter $fallback-l10n-file.</xsl:message>
  </xsl:param>

  <xsl:variable name="l10n-content" select="document($l10n-file)/l:locale"/>
  <xsl:variable name="fallback-l10n-content" select="document($fallback-l10n-file)/l:locale"/>

  <xsl:template match="/f:fragment">
    <xsl:apply-templates select="*"/>
  </xsl:template>

  <xsl:template match="f:l10n">
    <xsl:param name="key" select="@select"/>
    <xsl:variable name="this-lang" select="$l10n-content/@lang"/>
    <xsl:variable name="fallback-lang" select="$fallback-l10n-content/@lang"/>
    <xsl:choose>
      <xsl:when test="$l10n-content/l:content[@key = $key]">
        <xsl:apply-templates select="$l10n-content/l:content[@key = $key]/node()"/>
      </xsl:when>
      <xsl:when test="$fallback-l10n-content/l:content[@key = $key]">
        <xsl:apply-templates select="$fallback-l10n-content/l:content[@key = $key]/node()"/>
        <xsl:message><xsl:value-of select="$this-lang"/>: Falling back to <xsl:value-of select="$fallback-lang"/> for localization key "<xsl:value-of select="$key"/>".</xsl:message>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message terminate="yes">Localization key "<xsl:value-of select="$key"/>" is not defined. Aborting.</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="@f:l10n|@f:*[starts-with(local-name(.), 'l10n-')]">
    <xsl:param name="attribute" select="substring-before(., '|')"/>
    <xsl:param name="key" select="substring-after(., '|')"/>
    <xsl:choose>
      <xsl:when test="$l10n-content/l:content[@key = $key]">
        <xsl:attribute name="{$attribute}">
          <xsl:value-of select="normalize-space($l10n-content/l:content[@key = $key]/text())"/>
        </xsl:attribute>
      </xsl:when>
      <xsl:when test="$fallback-l10n-content/l:content[@key = $key]">
        <xsl:attribute name="{$attribute}">
          <xsl:value-of select="normalize-space($fallback-l10n-content/l:content[@key = $key]/text())"/>
        </xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message terminate="yes">Localization key "<xsl:value-of select="$key"/>" is not defined.</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- In general, we want output without comments. However, we need to keep at
  least the ICP comment for Chinese regulators. -->
  <xsl:template match="f:comment">
    <xsl:comment><xsl:value-of select="text()"/></xsl:comment>
  </xsl:template>

  <xsl:template match="f:br">
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- We are not using the normal copy template: we want to remove /all/ namespaces from the output. -->
  <xsl:template match="*">
    <xsl:element name="{local-name()}">
      <xsl:for-each select="@*[not(starts-with(name(.), 'f:l10n'))]">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:apply-templates select="@f:l10n|@f:l10n-2|@f:l10n-3|*|text()"/>
    </xsl:element>
    <xsl:if test="/f:fragment/@f:force-breaks='yes'">
      <xsl:text>&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="text()"><xsl:value-of select="."/></xsl:template>

</xsl:stylesheet>
