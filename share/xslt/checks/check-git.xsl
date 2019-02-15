<?xml version="1.0" encoding="UTF-8"?>
<!--
   Purpose:
     Check if we have at least one <git> element, either in

       * /product/git, or
       * /product/docset/builddocs/git

     This is kind of "dummy check" as the RNG schema requires
     a /product/git element 

  Parameters:
     None
       
   Input:
     XML instance of config-validation.rnc
     
   Output:
     "0" = success
     "10" = failure
  
   Author:    Thomas Schraitle <toms@opensuse.org>
   Copyright (C) 2019 SUSE Linux GmbH

-->
<xsl:stylesheet version="1.0"
    xmlns:d="http://docbook.org/ns/docbook"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="d">

    <xsl:import href="log.xsl"/>
    <xsl:output method="text"/>

    <xsl:template match="/product">
        <xsl:call-template name="git.check"/>
    </xsl:template>

    <d:para>Checks whether at least one Git repository is definied inside a <d:tag>git</d:tag> tag.</d:para>
    <xsl:template name="git.check">
        <xsl:variable name="global.git" select="git"/>
        <xsl:variable name="local.git" select="docset/builddocs/git"/>
        <xsl:if test="count($global.git | $local.git) = 0">
            <xsl:call-template name="log.error">
                <xsl:with-param name="msg">
                    <xsl:text>The XML file contains no git element, but I've expected one.</xsl:text>
                </xsl:with-param>
            </xsl:call-template>
            <xsl:text>1</xsl:text>
        </xsl:if>
        <xsl:text>0</xsl:text>
    </xsl:template>
</xsl:stylesheet>