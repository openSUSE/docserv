<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <!-- HTML-in-JSON escaping -->

  <xsl:template match="*" mode="escape-html">
    <xsl:text>&lt;</xsl:text><xsl:value-of select="local-name(.)"/>
    <xsl:apply-templates select="@*" mode="escape-html"/>
    <xsl:text>&gt;</xsl:text>
    <xsl:apply-templates select="text()|*" mode="escape-html"/>
    <xsl:text>&lt;/</xsl:text><xsl:value-of select="local-name(.)"/><xsl:text>&gt;</xsl:text>
  </xsl:template>

  <xsl:template match="@*" mode="escape-html">
    <xsl:text> </xsl:text><xsl:value-of select="local-name(.)"/><xsl:text>=\&quot;</xsl:text>
    <xsl:call-template name="escape-text">
      <xsl:with-param name="use-single-quote-only" select="true"/>
    </xsl:call-template>
    <xsl:text>\&quot;</xsl:text>
  </xsl:template>

  <xsl:template match="text()" mode="escape-html">
    <xsl:call-template name="escape-text"/>
  </xsl:template>

  <xsl:template name="escape-text" mode="escape-html">
    <xsl:param name="input" select="."/>
    <xsl:param name="use-single-quote-only" select="false"/>

    <!-- Remove deadweight strings that consist of only spaces and newlines -->
    <xsl:variable name="text-remove-empty">
      <xsl:choose>
        <xsl:when test="not(translate($input,' &#10;',''))">
          <xsl:text/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$input"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <!-- Newlines need to be escaped as \\n for JSON. -->
    <xsl:variable name="text-fix-newline">
      <xsl:call-template name="string-replace">
        <xsl:with-param name="input" select="$text-remove-empty"/>
        <xsl:with-param name="search-string" select="'&#10;'"/>
        <xsl:with-param name="replace-string" select="'\\n'"/>
      </xsl:call-template>
    </xsl:variable>

    <!-- Replace literal backslashes -->
    <xsl:variable name="text-fix-backslash">
      <xsl:call-template name="string-replace">
        <xsl:with-param name="input" select="$text-fix-newline"/>
        <xsl:with-param name="search-string" select="'\'"/>
        <xsl:with-param name="replace-string" select="'\\'"/>
      </xsl:call-template>
    </xsl:variable>

    <!-- Quotes are used to delimit strings in JSON. -->
    <xsl:variable name="text-fix-quote">
      <xsl:choose>
        <xsl:when test="$use-single-quote-only = true">
          <xsl:call-template name="string-replace">
            <xsl:with-param name="input" select="$text-fix-newline"/>
            <xsl:with-param name="search-string" select="'&quot;'"/>
            <xsl:with-param name="replace-string" select='"&apos;"'/>
          </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
          <xsl:call-template name="string-replace">
            <xsl:with-param name="input" select="$text-fix-newline"/>
            <xsl:with-param name="search-string" select="'&quot;'"/>
            <xsl:with-param name="replace-string" select="'\&quot;'"/>
          </xsl:call-template>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="$text-fix-quote"/>
  </xsl:template>

</xsl:stylesheet>
