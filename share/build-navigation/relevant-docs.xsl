<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet
[
  <!ENTITY sortlower "abcdefghijklmnopqrstuvwxyz">
  <!ENTITY sortupper "ABCDEFGHIJKLMNOPQRSTUVWXYZ">
]>

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:dscr="https://github.com/openSUSE/docserv/docserv2_cache_result">

  <xsl:template name="list-existing-sets">
    <xsl:param name="list" select="'supported'"/>
    <xsl:text> </xsl:text>
    <xsl:for-each select="//product/docset">
      <xsl:if
        test="((
               $list = 'supported' and
               (@lifecycle = 'beta' or @lifecycle = 'supported' or
               (@lifecycle = 'unpublished' and $internal_mode = 'true'))
              ) or (
               $list = 'unsupported' and
               @lifecycle = 'unsupported'
              )) and
              (not(@navigation-visible = 'hidden') or $internal_mode = 'true')
              ">
          <xsl:choose>
            <xsl:when test="builddocs">
              <xsl:variable name="productid" select="ancestor::product/@productid"/>
              <xsl:variable name="setid" select="@setid"/>
              <xsl:variable name="default-language" select="builddocs/language[@default = 'true']/@lang"/>
              <xsl:if test="$cache_content/*[self::document or self::archive][@productid = $productid][@setid = $setid][@lang = $default-language]">
                <xsl:value-of select="concat(ancestor::product/@productid,'/',@setid)"/>
                <xsl:text> </xsl:text>
              </xsl:if>
            </xsl:when>
            <!-- Should always be there and getting updated anyway because it
            does not need to actually be built. -->
            <xsl:otherwise>
              <xsl:value-of select="concat(ancestor::product/@productid,'/',@setid)"/>
              <xsl:text> </xsl:text>
            </xsl:otherwise>
          </xsl:choose>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>
