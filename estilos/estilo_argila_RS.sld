<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0" xmlns:sld="http://www.opengis.net/sld">
  <UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Name>ARGILA_RS_TEOR</sld:Name>
      <sld:FeatureTypeStyle>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ChannelSelection>
              <sld:GrayChannel>
                <sld:SourceChannelName>1</sld:SourceChannelName>
              </sld:GrayChannel>
            </sld:ChannelSelection>
            <sld:ColorMap type="intervals">
              <sld:ColorMapEntry color="#ffffd4" quantity="133" label="&lt;= 133"/>
              <sld:ColorMapEntry color="#ffffd4" quantity="186.66666666666666" label="133 - 187"/>
              <sld:ColorMapEntry color="#ffecb1" quantity="240.33333333333331" label="187 - 240"/>
              <sld:ColorMapEntry color="#fed98e" quantity="294" label="240 - 294"/>
              <sld:ColorMapEntry color="#feb95c" quantity="347.66666666666663" label="294 - 348"/>
              <sld:ColorMapEntry color="#fe9929" quantity="401.33333333333331" label="348 - 401"/>
              <sld:ColorMapEntry color="#ec7c1c" quantity="455" label="401 - 455"/>
              <sld:ColorMapEntry color="#d95f0e" quantity="508.66666666666663" label="455 - 509"/>
              <sld:ColorMapEntry color="#b94a09" quantity="562.33333333333326" label="509 - 562"/>
              <sld:ColorMapEntry color="#993404" quantity="616" label="562 - 616"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </UserLayer>
</StyledLayerDescriptor>
