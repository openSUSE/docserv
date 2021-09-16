<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  exclude-result-prefixes="">

  <xsl:output method="xml" indent="yes"/>


  <xsl:template match="comment()|processing-instruction()"/>
  <xsl:template match="language/@translation-type"/>

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


  <xsl:template match="deliverable/subdir">
    <xsl:param name="ignore-subdir" select="0"/>
    <xsl:if test="$ignore-subdir != 1">
      <xsl:element name="{local-name(.)}">
        <xsl:apply-templates select="@*|*|text()"/>
      </xsl:element>
    </xsl:if>
  </xsl:template>


  <xsl:template match="format/@*|@default|version/@includes-productname|listingversion/@includes-productname">
    <xsl:attribute name="{local-name(.)}">
      <xsl:choose>
        <xsl:when test=". = 1 or . = 'true'">true</xsl:when>
        <xsl:when test=". = 0 or . = 'false'">false</xsl:when>
      </xsl:choose>
    </xsl:attribute>
  </xsl:template>


  <xsl:template match="/docservconfig">
    <positivedocservconfig>
      <xsl:apply-templates select="@*|*"/>
    </positivedocservconfig>
  </xsl:template>

  <xsl:template match="language[not(@default) or @default='false' or @default='0'][@translation-type='list']">
    <language>
      <xsl:apply-templates select="@*|*[not(self::deliverable)]"/>
      <xsl:apply-templates select="deliverable" mode="find_extra_elements"/>
    </language>
  </xsl:template>

  <xsl:template match="deliverable" mode="find_extra_elements">
    <xsl:variable name="current_dc" select="dc"/>
    <deliverable>
      <xsl:apply-templates select="@*"/>
      <xsl:apply-templates select="dc"/>
      <!-- subdir is inheritable but overwritable, i.e. there must only be one -->
      <xsl:apply-templates select="subdir"/>
      <xsl:apply-templates select="parent::language/preceding-sibling::language[@default='true' or @default='1']/deliverable[dc = $current_dc]/*[not(self::dc or self::subdeliverable)]">
        <xsl:with-param name="ignore-subdir">
          <xsl:if test="subdir">1</xsl:if>
        </xsl:with-param>
      </xsl:apply-templates>
      <xsl:apply-templates select="subdeliverable"/>
    </deliverable>
  </xsl:template>


  <xsl:template match="language[not(@default) or @default='false' or @default='0'][@translation-type='full']">
    <language>
      <xsl:apply-templates select="@*|*"/>
      <xsl:apply-templates select="preceding-sibling::language[@default='true' or @default='1']/deliverable"/>
    </language>
  </xsl:template>


</xsl:stylesheet>
