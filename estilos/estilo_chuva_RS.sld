<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0" xmlns:sld="http://www.opengis.net/sld">
  <UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Name>Recortado (mascara)</sld:Name>
      <sld:FeatureTypeStyle>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ChannelSelection>
              <sld:GrayChannel>
                <sld:SourceChannelName>1</sld:SourceChannelName>
              </sld:GrayChannel>
            </sld:ChannelSelection>
            <sld:ColorMap type="intervals">
              <sld:ColorMapEntry color="#f7fbff" quantity="0" label="&lt;= 0,0000"/>
              <sld:ColorMapEntry color="#f7fbff" quantity="1302.5" label="0,0000 - 1302,5000"/>
              <sld:ColorMapEntry color="#e2edf8" quantity="1435" label="1302,5000 - 1435,0000"/>
              <sld:ColorMapEntry color="#cde0f1" quantity="1567.5" label="1435,0000 - 1567,5000"/>
              <sld:ColorMapEntry color="#afd1e7" quantity="1700" label="1567,5000 - 1700,0000"/>
              <sld:ColorMapEntry color="#89bedc" quantity="1832.5" label="1700,0000 - 1832,5000"/>
              <sld:ColorMapEntry color="#60a6d2" quantity="1965" label="1832,5000 - 1965,0000"/>
              <sld:ColorMapEntry color="#3e8ec4" quantity="2097.5" label="1965,0000 - 2097,5000"/>
              <sld:ColorMapEntry color="#2272b5" quantity="2230" label="2097,5000 - 2230,0000"/>
              <sld:ColorMapEntry color="#0a549e" quantity="2362.5" label="2230,0000 - 2362,5000"/>
              <sld:ColorMapEntry color="#08306b" quantity="2500" label="2362,5000 - 2500,0000"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </UserLayer>
</StyledLayerDescriptor>
