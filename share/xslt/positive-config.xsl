<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  exclude-result-prefixes="">

  <xsl:output method="xml" indent="yes"/>


  <xsl:template match="comment()|processing-instruction()"/>


  <xsl:template match="*" priority="-1">
    <xsl:element name="{local-name(.)}">
      <xsl:apply-templates select="@*|*|text()"/>
    </xsl:element>
  </xsl:template>


  <xsl:template match="@*" priority="-1">
    <xsl:attribute name="{local-name(.)}">
      <xsl:value-of select="."/>
    </xsl:attribute>
  </xsl:template>


  <xsl:template match="text()" priority="-1">
    <xsl:value-of select="."/>
  </xsl:template>


  <xsl:template match="/docservconfig">
    <positivedocservconfig>
      <xsl:apply-templates select="@*|*"/>
    </positivedocservconfig>
  </xsl:template>


  <xsl:template match="language[not(@default) or @default='false' or @default='0']">
    <xsl:variable name="blacklist">
      <xsl:apply-templates select="untranslated/deliverable" mode="create-blacklist-param"/>
    </xsl:variable>
    <language>
      <xsl:apply-templates select="@*|*[not(self::deliverable)]"/>
      <xsl:apply-templates select="preceding-sibling::language[@default='true' or @default='1']/deliverable" mode="positize">
        <xsl:with-param name="blacklist" select="$blacklist"/>
        <xsl:with-param name="langcode" select="@lang"/>
      </xsl:apply-templates>
    </language>
  </xsl:template>


  <xsl:template match="deliverable" mode="create-blacklist-param">
    <xsl:param name="DC" select="dc"/>
    <xsl:variable name="add-to-list">
      <xsl:choose>
        <xsl:when test="subdeliverable">
          <xsl:variable name="translated-subdeliverables">
            <xsl:for-each select="subdeliverable">
              <xsl:sort select="translate(., ' &#10;', '')" order="descending"/>
              <xsl:value-of select="translate(., ' &#10;', '')"/>
              <xsl:text> </xsl:text>
            </xsl:for-each>
          </xsl:variable>
          <xsl:variable name="original-subdeliverables">
            <xsl:if test="ancestor::builddocs/language[@default='true' or @default='1']/deliverable[dc = $DC][subdeliverable]">
              <xsl:for-each select="ancestor::builddocs/language[@default='true' or @default='1']/deliverable[dc = $DC][subdeliverable]/subdeliverable">
                <xsl:sort select="translate(., ' &#10;', '')" order="descending"/>
                <xsl:value-of select="translate(., ' &#10;', '')"/>
                <xsl:text> </xsl:text>
              </xsl:for-each>
            </xsl:if>
          </xsl:variable>
          <xsl:choose>
            <xsl:when test="$translated-subdeliverables = $original-subdeliverables or $original-subdeliverables = ''">1</xsl:when>
            <xsl:otherwise>0</xsl:otherwise>
          </xsl:choose>
        </xsl:when>
        <xsl:otherwise>1</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:if test="$add-to-list = 1">
      <xsl:value-of select="$DC"/>
      <xsl:text> </xsl:text>
    </xsl:if>
  </xsl:template>


  <xsl:template match="deliverable" mode="positize">
    <xsl:param name="blacklist" select="''"/>
    <xsl:param name="langcode" select="''"/>
    <xsl:if test="not(contains(concat(' ', $blacklist, ' '), concat(' ', dc, ' ')))">
      <deliverable>
        <xsl:apply-templates select="@*|*[not(self::subdeliverable or self::untranslated)]"/>
        <xsl:apply-templates select="subdeliverable" mode="positize">
          <xsl:with-param name="langcode" select="$langcode"/>
        </xsl:apply-templates>
      </deliverable>
    </xsl:if>
  </xsl:template>


  <xsl:template match="subdeliverable" mode="positize">
    <xsl:param name="langcode" select="''"/>
    <xsl:variable name="DC" select="preceding-sibling::dc[1]"/>
    <xsl:variable name="SUB" select="."/>
    <xsl:if test="not(ancestor::docset/builddocs/language[@lang = $langcode]/untranslated/deliverable[dc = $DC and subdeliverable = $SUB])">
      <xsl:apply-templates select="self::*"/>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
