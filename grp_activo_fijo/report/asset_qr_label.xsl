<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema">

	<xsl:template match="etikettseite">
		<document filename="Etikett.pdf">
			<template pageSize="(62mm, 29mm)"
					leftMargin="1.4mm" rightMargin="1.4mm" topMargin="0mm" bottomMargin="0mm"
					title="Etikett" author="Generated by Open ERP">
				<pageTemplate id="all">
					<frame id="first" x1="0" y1="0" width="62mm" height="29mm"/>
				</pageTemplate>
			</template>

			<stylesheet>
				<paraStyle name="st_product" fontName="Helvetica" leading="0" fontSize="7"  spaceBefore="0"   spaceAfter="0"/>
				<paraStyle name="st_loc"     fontName="Helvetica" leading="0" fontSize="3"  spaceBefore="0"   spaceAfter="0" alignment="left"/>
				<paraStyle name="st_slogan"  fontName="Helvetica" leading="3" fontSize="7"  spaceBefore="0"   spaceAfter="0" alignment="left"/>

				<blockTableStyle id="mytable" border="0">
					<blockLeftPadding length = "0"/>
					<blockTopPadding length = "0"/>
					<blockAlignment value="CENTER" start="0,0" stop="0,0"/>/>
					<blockValign value="MIDDLE"/>
					<lineStyle kind="GRID" colorName="white" thickness="0"/>
				</blockTableStyle>
			</stylesheet>

			<story>
				<xsl:apply-templates select="produktetikett" mode="story"/>
			</story>
		</document>
	</xsl:template>


	<xsl:template match="produktetikett" mode="story">

		<blockTable style="mytable" colWidths="80,80" rowHeights="70">
			<!--<xsl:if test="state!='draft'">-->
			<tr>
				<td>
					<image height="75" width="75"><xsl:value-of select="grafico_qr"/></image>
				</td>
				<td>
					<para style="st_slogan">
						<xsl:value-of select="company_name"/>
					</para>
					<spacer length="5mm"/>
					<para style="st_product">
						<xsl:value-of select="numero_activo"/>
					</para>
					<spacer length="5mm"/>
				</td>
			</tr>
			<!--</xsl:if>-->
		</blockTable>

	</xsl:template>

</xsl:stylesheet>