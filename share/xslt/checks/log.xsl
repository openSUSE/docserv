<?xml version="1.0" encoding="UTF-8"?>
<!--
   Purpose:
     Outputs logging messages
     
   Parameters:
     None
       
   Input:
     None
     
   Output:
     Messages with xsl:message, sometimes terminates
  
   Author:    Thomas Schraitle <toms@opensuse.org>
   Copyright (C) 2019 SUSE Linux GmbH

-->
<xsl:stylesheet  version="1.0"
    xmlns:d="http://docbook.org/ns/docbook"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="d">

    <xsl:template name="log">
        <xsl:param name="abort">no</xsl:param>
        <xsl:param name="msg"/>
        <xsl:variable name="msg.tmp" select="concat(normalize-space($msg), '&#10;')"/>
        
        <!-- Hint: The xsl:choose is necessary here as the terminate
                   attribute doesn't allow to configure it via AVT.
        -->
        <xsl:choose>
            <xsl:when test="$abort = 'no' or $abort = ''">
                <xsl:message><xsl:value-of select="$msg.tmp"/></xsl:message>
            </xsl:when>
            <xsl:otherwise>
                <xsl:message terminate="yes"><xsl:value-of select="$msg.tmp"/></xsl:message>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template name="log.error">
        <xsl:param name="msg"/>
        <xsl:call-template name="log">
            <xsl:with-param name="msg" select="concat('ERROR: ', $msg)"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="log.warn">
        <xsl:param name="msg"/>
        <xsl:call-template name="log">
            <xsl:with-param name="msg" select="concat('WARNING: ', $msg)"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="log.fatal">
        <xsl:param name="msg"/>
        <xsl:call-template name="log">
            <xsl:with-param name="msg" select="concat('FATAL: ', $msg)"/>
            <xsl:with-param name="abort">yes</xsl:with-param>
        </xsl:call-template>
    </xsl:template>

</xsl:stylesheet>