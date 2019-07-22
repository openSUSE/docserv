<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<!-- Check all references within the stitched stylesheet, so we can verify they
all exist. -->


  <xsl:output method="text"/>

  <xsl:template match="node()|@*"/>

  <xsl:template match="/">
    <xsl:apply-templates select="//ref"/>
  </xsl:template>

  <xsl:template match="ref">
    <xsl:variable name="product" select="@product"/>
    <xsl:variable name="docset" select="@docset"/>
    <xsl:variable name="dc" select="@dc"/>
    <xsl:variable name="subdeliverable" select="@subdeliverable"/>
    <xsl:variable name="link" select="@link"/>
    <xsl:choose>
      <xsl:when test="@subdeliverable and @dc and @docset and @product">
        <xsl:if
          test="not(//product[@productid = $product]/docset[@setid = $docset]/builddocs/language[@default = 'true' or @default = 1]/deliverable[dc = $dc][subdeliverable = $subdeliverable])">
          <xsl:text>Reference (ref) to </xsl:text>
          <xsl:value-of select="concat($product, '/', $docset, ':', $dc, '#', $subdeliverable)"/>
          <xsl:text> failed. Referenced subdeliverable does exist.</xsl:text>
          <xsl:text>&#10;---&#10;</xsl:text>
        </xsl:if>
      </xsl:when>
      <xsl:when test="@dc and @docset and @product">
        <xsl:choose>
          <!-- FIXME: I wonder if a reference to an element with
          subdeliverables is actually a valid use case. -->
          <xsl:when
            test="//product[@productid = $product]/docset[@setid = $docset]/builddocs/language[@default = 'true' or @default = 1]/deliverable[dc = $dc][subdeliverable]">
            <xsl:text>Reference (ref) to </xsl:text>
            <xsl:value-of select="concat($product, '/', $docset, ':', $dc)"/>
            <xsl:text> failed. Referenced deliverable has subdeliverables, you must choose a subdeliverable in your reference.</xsl:text>
            <xsl:text>&#10;---&#10;</xsl:text>
          </xsl:when>
          <xsl:when
            test="not(//product[@productid = $product]/docset[@setid = $docset]/builddocs/language[@default = 'true' or @default = 1]/deliverable[dc = $dc][not(subdeliverable)])">
            <xsl:text>Reference (ref) to </xsl:text>
            <xsl:value-of select="concat($product, '/', $docset, ':', $dc)"/>
            <xsl:text> failed. Referenced deliverable does not exist.</xsl:text>
            <xsl:text>&#10;---&#10;</xsl:text>
          </xsl:when>
        </xsl:choose>
      </xsl:when>
      <xsl:when test="@link and @docset and @product">
        <xsl:if
          test="not(//product[@productid = $product]/docset[@setid = $docset]/external/link[@linkid = $link])">
          <xsl:text>Reference (ref) to </xsl:text>
          <xsl:value-of select="concat($product, '/', $docset, '@', $link)"/>
          <xsl:text> failed. Referenced external link does not exist.</xsl:text>
          <xsl:text>&#10;---&#10;</xsl:text>
        </xsl:if>
      </xsl:when>
      <xsl:when test="@docset and @product">
        <xsl:if
          test="not(//product[@productid = $product]/docset[@setid = $docset])">
          <xsl:text>Reference (ref) to </xsl:text>
          <xsl:value-of select="concat($product, '/', $docset)"/>
          <xsl:text> failed. Referenced docset does not exist.</xsl:text>
          <xsl:text>&#10;---&#10;</xsl:text>
        </xsl:if>
      </xsl:when>
      <xsl:when test="@product">
        <xsl:if
          test="not(//product[@productid = $product])">
          <xsl:text>Reference (ref) to </xsl:text>
          <xsl:value-of select="concat($product, '/', $docset)"/>
          <xsl:text> failed. Referenced product does not exist.</xsl:text>
          <xsl:text>&#10;---&#10;</xsl:text>
        </xsl:if>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>Reference failed. This issue should have been caught by the RNC validation. This is a docserv-stitch bug.</xsl:text>
        <xsl:text>&#10;---&#10;</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
