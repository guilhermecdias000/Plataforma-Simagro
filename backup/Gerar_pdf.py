import os
import geopandas as gpd
import rasterio
import rasterio.mask
import requests
import json
import numpy as np
import logging
import ee
import pyproj
from shapely.ops import transform as shapely_transform, unary_union
from shapely.geometry import mapping, Point, MultiPolygon, Polygon
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
from xml.etree import ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from staticmap import StaticMap, Line
from io import BytesIO
from PIL import Image
import tempfile

# --- BIBLIOTECAS PARA O SERVIDOR ---
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

# --- CONFIGURAÇÃO INICIAL ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # A inicialização do projeto é opcional, mas pode ajudar em alguns casos
    ee.Initialize(project='ee-projetoumidade')
    logging.info("Google Earth Engine inicializado com sucesso.")
except Exception as e:
    logging.info("Tentando autenticar no Earth Engine...")
    ee.Authenticate()
    ee.Initialize(project='ee-projetoumidade')

# --- CAMINHOS PARA OS DADOS LOCAIS ---
BASE_DIR = "/home/joao-de-barro/BASE_CARTOGRAFIA"
tif_chuva = os.path.join(BASE_DIR, "DADOS/MERGE_CPTEC_media_2014-2024.tif")
tif_mapbiomas = os.path.join(BASE_DIR, "DADOS/mapbiomas_10m_collection2_integration_v1-classification_2023.tif")
tif_argila = os.path.join(BASE_DIR, "DADOS/ARGILA_BRASIL.tif")
qml_path = os.path.join(BASE_DIR, "ESTILO/ESTILO_QGIS_COL9.qml")
caminho_municipios = os.path.join(BASE_DIR, "LIMITES/BR_Municipios_2022/BR_Municipios_2022.shp")
caminho_centros = os.path.join(BASE_DIR, "INFRAESTRUTURA/GEOFT_CIDADE_2016/GEOFT_CIDADE_2016.shp")


# --- FUNÇÕES AUXILIARES ---
def formatar_numero(valor):
    try:
        valor_float = float(valor)
        partes = f"{valor_float:,.1f}".split(".")
        inteiro = partes[0].replace(",", ".")
        return f"{inteiro},{partes[1]}"
    except (ValueError, TypeError):
        return str(valor)

def clean_geometry(geometry):
    """
    Remove recursivamente a coordenada Z de uma geometria em formato de dicionário GeoJSON.
    """
    def clean_coords(coords):
        return [[coord[:2] for coord in ring] for ring in coords]

    # Lida com GeometryCollection extraindo os polígonos
    if geometry.get('type') == 'GeometryCollection':
        all_polygons = []
        for geom_part in geometry.get('geometries', []):
             if geom_part.get('type') == 'Polygon':
                all_polygons.append(geom_part['coordinates'])
             elif geom_part.get('type') == 'MultiPolygon':
                all_polygons.extend(geom_part['coordinates'])
        
        # Reconstrói a geometria como um MultiPolygon
        geometry = {
            "type": "MultiPolygon",
            "coordinates": all_polygons
        }

    if geometry["type"] == "Polygon":
        geometry["coordinates"] = clean_coords(geometry["coordinates"])
    elif geometry["type"] == "MultiPolygon":
        geometry["coordinates"] = [clean_coords(poly) for poly in geometry["coordinates"]]
            
    return geometry

def obter_municipio_da_fazenda(gdf, caminho_municipios_shp):
    try:
        municipios = gpd.read_file(caminho_municipios_shp).to_crs(gdf.crs)
        intersec = gpd.sjoin(gdf, municipios, how="left", predicate="intersects")
        if not intersec.empty and "NM_MUN" in intersec.columns and "SIGLA_UF" in intersec.columns:
            return f"{intersec.iloc[0]['NM_MUN']}, {intersec.iloc[0]['SIGLA_UF']}"
    except Exception as e:
        logging.error(f"Erro ao obter município: {e}")
    return "Não determinado"

def centros_urbanos_osrm(centro_fazenda, caminho_centros_shp, n=3):
    try:
        centros_4326 = gpd.read_file(caminho_centros_shp).to_crs(epsg=4326)
        ponto_ref = Point(centro_fazenda)
        centros_proj = centros_4326.to_crs(epsg=32722)
        ponto_ref_proj = gpd.GeoSeries([ponto_ref], crs="EPSG:4326").to_crs(epsg=32722).iloc[0]
        centros_proj["dist_reta"] = centros_proj.geometry.distance(ponto_ref_proj)
        candidatos = centros_4326.loc[centros_proj.nsmallest(10, "dist_reta").index]
        resultados = []
        for _, row in candidatos.iterrows():
            destino_coords = f"{row.geometry.x},{row.geometry.y}"
            origem_coords = f"{centro_fazenda[0]},{centro_fazenda[1]}"
            url = f"http://router.project-osrm.org/route/v1/driving/{origem_coords};{destino_coords}?overview=false"
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if 'routes' in data and data['routes']:
                    resultados.append((row["CID_NM"], row.get("CID_SG_UF", ""), round(data['routes'][0]['distance'] / 1000, 2)))
            except requests.RequestException as e:
                logging.warning(f"Erro OSRM para {row['CID_NM']}: {e}")
            if len(resultados) >= n: break
        return resultados
    except Exception as e:
        logging.error(f"Erro ao calcular centros urbanos: {e}")
        return []

def extrair_legenda_qml(caminho_qml):
    legenda = {}
    try:
        tree = ET.parse(caminho_qml)
        for elem in tree.iter('paletteEntry'):
            legenda[int(elem.attrib.get('value'))] = elem.attrib.get('label', "Classe")
    except Exception as e:
        logging.warning(f"Erro ao ler legenda QML: {e}")
    return legenda

def gerar_imagem_bing_memoria(gdf):
    gdf_4326 = gdf.to_crs(epsg=4326)
    m = StaticMap(800, 600, url_template='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')
    geom = unary_union(gdf_4326.geometry)
    
    def add_geom_to_map(geometry, map_obj):
        if isinstance(geometry, Polygon):
            map_obj.add_line(Line(list(geometry.exterior.coords), 'yellow', 3))
        elif isinstance(geometry, MultiPolygon):
            for part in geometry.geoms:
                map_obj.add_line(Line(list(part.exterior.coords), 'yellow', 3))

    add_geom_to_map(geom, m)
    image = m.render()
    img_buffer = BytesIO()
    image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer

mapbiomas_legenda = extrair_legenda_qml(qml_path)

# --- LÓGICA PRINCIPAL DE GERAÇÃO DO RELATÓRIO ---
def gerar_relatorio_para_gdf(gdf):
    # PASSO 1: Preparação e Cálculos de Geometria
    logging.info("PASSO 1/9: Preparando a geometria...")

    gdf = gdf[~gdf.is_empty]
    if gdf.empty:
        raise ValueError("GeoDataFrame vazio após a limpeza inicial.")
    
    unified_geom = unary_union(gdf.geometry)
    gdf = gpd.GeoDataFrame([{'geometry': unified_geom, 'name': gdf.iloc[0].get('name', 'Fazenda_Sem_Nome')}], crs=gdf.crs)

    try:
        nome_fazenda = gdf.iloc[0]['name']
    except (KeyError, IndexError):
        nome_fazenda = "Fazenda_Sem_Nome"
    logging.info(f"Processando: {nome_fazenda}")

    gdf_utm = gdf.to_crs(epsg=32722)
    area_total_ha = gdf_utm.geometry.area.iloc[0] / 10000
    centroid_4326 = gdf.geometry.centroid.iloc[0]
    center_x_4326, center_y_4326 = centroid_4326.x, centroid_4326.y

    # PASSO 2: Localização
    logging.info("PASSO 2/9: Obtendo município e rotas OSRM...")
    municipio_nome = obter_municipio_da_fazenda(gdf, caminho_municipios)
    centros_proximos = centros_urbanos_osrm((center_x_4326, center_y_4326), caminho_centros)

    # PASSO 3: Rasters Locais
    logging.info("PASSO 3/9: Analisando rasters (Chuva e Argila)...")
    with rasterio.open(tif_chuva) as src:
        try:
            row, col = src.index(center_x_4326, center_y_4326)
            chuva_value = src.read(1)[row, col] if 0 <= row < src.height and 0 <= col < src.width else None
        except Exception:
            chuva_value = None

    with rasterio.open(tif_argila) as src:
        try:
            out_image, _ = rasterio.mask.mask(src, [gdf.geometry.iloc[0]], crop=True, filled=True, nodata=0)
            argila_vals = out_image[0][out_image[0] > 0] / 10
            argila_range = f"{int(np.nanmin(argila_vals))} a {int(np.nanmax(argila_vals))}%" if argila_vals.size > 0 else "N/D"
        except ValueError:
            logging.warning("Geometria não intercepta o raster de argila.")
            argila_range = "N/D"

    # PASSO 4: Altitude GEE
    logging.info("PASSO 4/9: Consultando GEE para altitude...")
    geojson_dict = json.loads(gdf.to_json())
    geometry_cleaned = clean_geometry(geojson_dict["features"][0]["geometry"])
    
    feature = ee.Feature(ee.Geometry(geometry_cleaned))
    
    elevation_img = ee.Image("USGS/SRTMGL1_003")
    elevation_stats = elevation_img.reduceRegion(reducer=ee.Reducer.minMax(), geometry=feature.geometry(), scale=30, maxPixels=1e9).getInfo()
    alt_min, alt_max = elevation_stats.get("elevation_min"), elevation_stats.get("elevation_max")
    altitude_range = f"{int(alt_min)} a {int(alt_max)}m" if alt_min is not None else "N/D"
    
    # PASSO 5: Declividade
    logging.info("PASSO 5/9: Calculando declividade com GEE...")
    dem = ee.Image("USGS/SRTMGL1_003"); slope = ee.Terrain.slope(dem).clip(feature.geometry())
    slope_url = slope.getDownloadURL({'scale': 30, 'region': feature.geometry().bounds().getInfo()['coordinates'], 'format': 'GEO_TIFF'})
    
    areas_declividade = {}
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as slope_temp_file:
        slope_temp_file.write(requests.get(slope_url).content)
        slope_tif_path = slope_temp_file.name

    with rasterio.open(slope_tif_path) as src:
        dst_crs = "EPSG:32722"
        transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy(); kwargs.update({'crs': dst_crs, 'transform': transform, 'width': width, 'height': height})
        reprojected_slope = np.empty((1, height, width), dtype=np.float32)
        reproject(source=rasterio.band(src, 1), destination=reprojected_slope, src_transform=src.transform, src_crs=src.crs, dst_transform=transform, dst_crs=dst_crs, resampling=Resampling.nearest)
        
        with MemoryFile() as memfile:
            with memfile.open(**kwargs) as dataset:
                dataset.write(reprojected_slope)
                out_image, _ = rasterio.mask.mask(dataset, [gdf_utm.geometry.iloc[0]], crop=True, filled=True, nodata=np.nan)
                masked_image = np.ma.masked_invalid(out_image[0])
        
        pixel_area = abs(kwargs['transform'][0] * kwargs['transform'][4])
        limites = [0, 3, 8, 20, 45, 75, float('inf')]; classes = ['Plano', 'Suave ondulado', 'Ondulado', 'Fortemente ondulado', 'Montanhoso', 'Escarpado']
        for i, nome in enumerate(classes):
            count = np.sum((masked_image >= limites[i]) & (masked_image < limites[i+1]))
            areas_declividade[nome] = round((count * pixel_area) / 10000, 2)
    os.remove(slope_tif_path)

    # PASSO 6: MapBiomas
    logging.info("PASSO 6/9: Calculando uso do solo (MapBiomas)...")
    try:
        mapbiomas_stats = {}
        logging.info("Abrindo raster MapBiomas: %s", tif_mapbiomas)
        with rasterio.open(tif_mapbiomas) as src:
            transformer = pyproj.Transformer.from_crs(gdf.crs.to_string(), src.crs.to_string(), always_xy=True).transform
            logging.info("Transformando geometria da fazenda para CRS do raster...")
            shape_geom_mapbiomas = shapely_transform(transformer, gdf.geometry.iloc[0])
            logging.info("Iniciando recorte da geometria no raster...")
            out_image, out_transform = rasterio.mask.mask(src, [shape_geom_mapbiomas], crop=True, filled=True, nodata=0)
            logging.info("Recorte realizado com sucesso. Formato da imagem: %s", out_image.shape)
            out_image = out_image[0]

            pixel_size_x = src.res[0]
            pixel_size_y = src.res[1]
            pixel_area_deg = abs(pixel_size_x * pixel_size_y)

            logging.info("Tamanho do pixel (graus): %.8f x %.8f", pixel_size_x, pixel_size_y)

            # Aproximação da área por pixel em hectares (graus para metros quadrados usando latitude média)
            centroid_lat = shape_geom_mapbiomas.centroid.y
            geod = pyproj.Geod(ellps='WGS84')
            pixel_area_m2_total, _ = geod.polygon_area_perimeter(
                [shape_geom_mapbiomas.bounds[0], shape_geom_mapbiomas.bounds[2], shape_geom_mapbiomas.bounds[2], shape_geom_mapbiomas.bounds[0]],
                [shape_geom_mapbiomas.bounds[1], shape_geom_mapbiomas.bounds[1], shape_geom_mapbiomas.bounds[3], shape_geom_mapbiomas.bounds[3]]
            )
            pixel_area_m2 = abs(pixel_area_m2_total) / (out_image.shape[0] * out_image.shape[1])
            pixel_area_ha = pixel_area_m2 / 10000
            logging.info("Área estimada por pixel (ha): %.4f", pixel_area_ha)

            unique, counts = np.unique(out_image[out_image > 0], return_counts=True)
            logging.info("Classes únicas encontradas: %s", unique)
            for cls, count in zip(unique, counts):
                area_ha_cls = count * pixel_area_ha
                perc = (area_ha_cls / area_total_ha) * 100 if area_total_ha > 0 else 0
                logging.info("Classe %s => Área: %.2f ha (%.2f%%)", cls, area_ha_cls, perc)
                mapbiomas_stats[int(cls)] = (round(area_ha_cls, 2), round(perc, 2))
    except Exception as e:
        logging.exception("Erro durante análise do MapBiomas: %s", e)
    # PASSO 7: Imagem
    logging.info("PASSO 7/9: Gerando imagem de satélite...")
    img_buffer = gerar_imagem_bing_memoria(gdf)
    
    # PASSO 8: PDF
    logging.info("PASSO 8/9: Montando o documento PDF...")
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4; margin_x, margin_top, line_height, section_gap = 40, 50, 12, 14
    current_y = height - margin_top
    def check_page_space(lines_needed):
        nonlocal current_y
        if current_y < lines_needed * line_height + 60: c.showPage(); current_y = height - margin_top
    
    c.setFont("Helvetica-Bold", 16); c.drawCentredString(width / 2, current_y, f"Relatório {nome_fazenda.replace('_', ' ')}"); current_y -= 25
    if img_buffer:
        img_width, img_height = 500, 325
        c.drawImage(ImageReader(img_buffer), margin_x, current_y - img_height, width=img_width, height=img_height)
        current_y -= (img_height + section_gap)
    
    check_page_space(5)
    c.setFont("Helvetica-Bold", 11); c.drawString(margin_x, current_y, "Informações da Área"); current_y -= line_height
    c.setFont("Helvetica", 10); c.drawString(margin_x + 10, current_y, f"Área total: {formatar_numero(area_total_ha)} ha"); current_y -= line_height
    c.drawString(margin_x + 10, current_y, f"Chuva média anual: {formatar_numero(chuva_value) if chuva_value else 'N/D'} mm"); current_y -= line_height
    c.drawString(margin_x + 10, current_y, f"Altitude: {altitude_range}"); current_y -= line_height
    c.drawString(margin_x + 10, current_y, f"Teor de argila: {argila_range}"); current_y -= section_gap

    check_page_space(4 + len(centros_proximos))
    c.setFont("Helvetica-Bold", 11); c.drawString(margin_x, current_y, "Localização"); current_y -= line_height
    c.setFont("Helvetica", 10); c.drawString(margin_x + 10, current_y, f"Município: {municipio_nome}"); current_y -= line_height
    c.drawString(margin_x + 10, current_y, "Cidades próximas (distância em rota):"); current_y -= line_height
    if centros_proximos:
        for nome, estado, dist_km in centros_proximos:
            c.drawString(margin_x + 20, current_y, f"- {nome} ({estado}): {formatar_numero(dist_km)} km"); current_y -= line_height
    else:
        c.drawString(margin_x + 20, current_y, "- Nenhuma cidade encontrada."); current_y -= line_height
    current_y -= section_gap

    check_page_space(len(areas_declividade) + 2)
    c.setFont("Helvetica-Bold", 11); c.drawString(margin_x, current_y, "Declividade do Terreno"); current_y -= line_height
    c.setFont("Helvetica", 10)
    for classe, area in sorted(areas_declividade.items(), key=lambda item: item[1], reverse=True):
        if area > 0.01:
            c.drawString(margin_x + 10, current_y, f"- {classe}: {formatar_numero(area)} ha"); current_y -= line_height
    current_y -= section_gap
    
    check_page_space(len(mapbiomas_stats) + 2)
    c.setFont("Helvetica-Bold", 11); c.drawString(margin_x, current_y, "Uso e Cobertura do Solo (MapBiomas)"); current_y -= line_height
    c.setFont("Helvetica", 10)
    sorted_mapbiomas = sorted(mapbiomas_stats.items(), key=lambda item: item[1][0], reverse=True)
    for cls, (area_ha, perc) in sorted_mapbiomas:
        nome = mapbiomas_legenda.get(cls, f"Classe {cls}")
        c.drawString(margin_x + 10, current_y, f"- {nome}: {formatar_numero(area_ha)} ha ({formatar_numero(perc)}%)"); current_y -= line_height

    c.save()
    
    logging.info("PASSO 9/9: Finalizando e retornando o buffer do PDF.")
    pdf_buffer.seek(0)
    return pdf_buffer

# --- ESTRUTURA DO SERVIDOR FLASK ---
app = Flask(__name__); CORS(app)

@app.route('/gerar-pdf', methods=['POST'])
def handle_pdf_generation():
    logging.info("Requisição '/gerar-pdf' recebida.")
    if not request.is_json:
        return jsonify({"error": "A requisição deve ser do tipo JSON"}), 400
    
    geojson_data = request.get_json()

    try:
        if geojson_data.get('type') == 'FeatureCollection':
            features = geojson_data['features']
        else:
            features = [geojson_data]
        if not features:
            return jsonify({"error": "Nenhuma feição encontrada no GeoJSON."}), 400
            
        gdf = gpd.GeoDataFrame.from_features(features)
        gdf.set_crs("EPSG:4326", inplace=True)
        
        if 'name' in features[0].get('properties', {}):
             gdf['name'] = features[0]['properties']['name']

        pdf_in_memory = gerar_relatorio_para_gdf(gdf)
        
        try:
            file_name = f"relatorio_{features[0].get('properties',{}).get('name','fazenda')}.pdf"
        except (IndexError, KeyError):
            file_name = "relatorio_fazenda.pdf"
            
        return send_file(pdf_in_memory, as_attachment=True, download_name=file_name.replace(" ", "_"), mimetype='application/pdf')
        
    except Exception as e:
        logging.exception("Erro crítico durante a geração do PDF.")
        return jsonify({"error": f"Ocorreu um erro no servidor: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

