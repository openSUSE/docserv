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


  <xsl:template match="format/@*|@default">
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

  <xsl:template match="language[not(@default) or @default='false' or @default='0'][@translation-type='positive-list']">
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


  <xsl:template match="language[not(@default) or @default='false' or @default='0'][@translation-type='negative-list']">
    <xsl:variable name="negative_list">
      <xsl:apply-templates select="deliverable" mode="create_negative_list"/>
    </xsl:variable>
    <language>
      <xsl:apply-templates select="@*|*[not(self::deliverable)]"/>
      <xsl:apply-templates select="preceding-sibling::language[@default='true' or @default='1']/deliverable" mode="apply_list">
        <xsl:with-param name="list" select="$negative_list"/>
        <xsl:with-param name="langcode" select="@lang"/>
      </xsl:apply-templates>
    </language>
  </xsl:template>

  <xsl:template match="deliverable" mode="create_negative_list">
    <xsl:param name="current-dc" select="dc"/>
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
            <xsl:if test="ancestor::builddocs/language[@default='true' or @default='1']/deliverable[dc = $current-dc][subdeliverable]">
              <xsl:for-each select="ancestor::builddocs/language[@default='true' or @default='1']/deliverable[dc = $current-dc][subdeliverable]/subdeliverable">
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
      <xsl:value-of select="$current-dc"/>
      <xsl:text> </xsl:text>
    </xsl:if>
  </xsl:template>


  <xsl:template match="deliverable" mode="apply_list">
    <xsl:param name="blacklist" select="''"/>
    <xsl:param name="langcode" select="''"/>
    <xsl:if test="not(contains(concat(' ', $blacklist, ' '), concat(' ', dc, ' ')))">
      <deliverable>
        <xsl:apply-templates select="@*|*[not(self::subdeliverable or self::untranslated)]"/>
        <xsl:apply-templates select="subdeliverable" mode="apply_list">
          <xsl:with-param name="langcode" select="$langcode"/>
        </xsl:apply-templates>
      </deliverable>
    </xsl:if>
  </xsl:template>


  <xsl:template match="subdeliverable" mode="apply_list">
    <xsl:param name="langcode" select="''"/>
    <xsl:variable name="current-dc" select="preceding-sibling::dc[1]"/>
    <xsl:variable name="current-subdeliverable" select="."/>
    <xsl:if test="not(ancestor::docset/builddocs/language[@lang = $langcode]/untranslated/deliverable[dc = $current-dc and subdeliverable = $current-subdeliverable])">
      <xsl:apply-templates select="self::*"/>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
