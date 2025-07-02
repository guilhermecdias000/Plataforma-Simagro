<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0" xmlns:sld="http://www.opengis.net/sld">
  <UserLayer>
    <sld:LayerFeatureConstraints>
      <sld:FeatureTypeConstraint/>
    </sld:LayerFeatureConstraints>
    <sld:UserStyle>
      <sld:Name>Chuva_Brasil_Merge  copiar</sld:Name>
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
              <sld:ColorMapEntry color="#f7fbff" quantity="620" label="0,0000 - 620,0000"/>
              <sld:ColorMapEntry color="#e2edf8" quantity="940" label="620,0000 - 940,0000"/>
              <sld:ColorMapEntry color="#cde0f1" quantity="1260" label="940,0000 - 1260,0000"/>
              <sld:ColorMapEntry color="#afd1e7" quantity="1580" label="1260,0000 - 1580,0000"/>
              <sld:ColorMapEntry color="#89bedc" quantity="1900" label="1580,0000 - 1900,0000"/>
              <sld:ColorMapEntry color="#60a6d2" quantity="2220" label="1900,0000 - 2220,0000"/>
              <sld:ColorMapEntry color="#3e8ec4" quantity="2540" label="2220,0000 - 2540,0000"/>
              <sld:ColorMapEntry color="#2272b5" quantity="2860" label="2540,0000 - 2860,0000"/>
              <sld:ColorMapEntry color="#0a549e" quantity="3180" label="2860,0000 - 3180,0000"/>
              <sld:ColorMapEntry color="#08306b" quantity="3500" label="3180,0000 - 3500,0000"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </UserLayer>
</StyledLayerDescriptor>
