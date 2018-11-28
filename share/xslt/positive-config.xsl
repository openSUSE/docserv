<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  exclude-result-prefixes="">

  <xsl:output method="xml" indent="yes"/>


  <xsl:template match="node()|@*"/>


  <xsl:template match="*" mode="take-all">
    <xsl:element name="{local-name(.)}">
      <xsl:apply-templates select="@*|*|text()" mode="take-all"/>
    </xsl:element>
  </xsl:template>


  <xsl:template match="@*" mode="take-all">
    <xsl:attribute name="{local-name(.)}">
      <xsl:value-of select="."/>
    </xsl:attribute>
  </xsl:template>


  <xsl:template match="text()" mode="take-all">
    <xsl:value-of select="."/>
  </xsl:template>


  <xsl:template match="/docservconfig">
    <positivedocservconfig>
      <xsl:apply-templates select="product"/>
    </positivedocservconfig>
  </xsl:template>


  <xsl:template match="product">
    <product productid="{@productid}">
      <xsl:apply-templates select="docset"/>
    </product>
  </xsl:template>


  <xsl:template match="docset">
    <docset setid="{@setid}">
      <xsl:apply-templates select="builddocs"/>
    </docset>
  </xsl:template>


  <xsl:template match="builddocs">
    <builddocs>
      <xsl:apply-templates select="git|language"/>
    </builddocs>
  </xsl:template>


  <xsl:template match="git">
    <git>
      <xsl:apply-templates select="*" mode="take-all"/>
    </git>
  </xsl:template>


  <xsl:template match="language[@default='true' or @default='1']">
    <language>
      <xsl:apply-templates select="@*|*" mode="take-all"/>
    </language>
  </xsl:template>


  <xsl:template match="language[not(@default) or @default='false' or @default='0']">
    <xsl:variable name="blacklist">
      <xsl:apply-templates select="untranslated/deliverable" mode="create-blacklist-param"/>
    </xsl:variable>
    <language>
      <xsl:apply-templates select="@*" mode="take-all"/>
      <xsl:apply-templates select="branch|subdir" mode="take-all"/>
      <xsl:apply-templates select="./preceding-sibling::language[@default='true' or @default='1']/deliverable" mode="positize">
        <xsl:with-param name="blacklist" select="$blacklist"/>
      </xsl:apply-templates>
    </language>
  </xsl:template>


  <xsl:template match="deliverable" mode="create-blacklist-param">
    <xsl:param name="dc" select="dc"/>
    <xsl:variable name="add-to-list">
      <xsl:choose>
        <xsl:when test="subdeliverable">
          <xsl:variable name="translated-subdeliverables">
            <xsl:for-each select="subdeliverable">
              <xsl:sort select="subdeliverable"/>
              <xsl:value-of select="translate(subdeliverable, ' &#10;', '')"/>
            </xsl:for-each>
          </xsl:variable>
          <xsl:variable name="original-subdeliverables">
            <!-- Not sure if [1] make any sense here... -->
            <xsl:if test="ancestor::builddocs/language[@default='true' or @default='1']/dc[. = $dc][subdeliverable]">
              <xsl:for-each select="ancestor::builddocs/language[@default='true' or @default='1']/dc[. = $dc][subdeliverable][1]/subdeliverable">
                <xsl:sort select="subdeliverable"/>
                <xsl:value-of select="translate(subdeliverable, ' &#10;', '')"/>
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
      <xsl:value-of select="$dc"/>
      <xsl:text> </xsl:text>
    </xsl:if>
  </xsl:template>


  <xsl:template match="deliverable" mode="positize">
    <xsl:param name="blacklist" select="''"/>
    <xsl:if test="not(contains(concat(' ', $blacklist, ' '), concat(' ', dc, ' ')))">
      <deliverable>
        <xsl:apply-templates select="@*|*" mode="take-all"/>
      </deliverable>
    </xsl:if>
  </xsl:template>


</xsl:stylesheet>
