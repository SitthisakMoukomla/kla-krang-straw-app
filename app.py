
import streamlit as st
import ee
import geemap.foliumap as geemap

# === กำหนดโลโก้และชื่อหน้า ===
st.set_page_config(page_title="ระบบประเมินฟางข้าว", layout="wide")

# === แสดงโลโก้บริษัท ===
st.image("378034341_330380276014601_880975176463400977_n.jpg", width=120)
st.markdown("""
# ระบบประเมินปริมาณฟางข้าวเพื่อบริหารจัดการชีวมวล  
### บริษัท กล้า-แกร่ง จำกัด • จังหวัดนครสวรรค์
""")

# === Authenticate Earth Engine ===
ee.Authenticate()
ee.Initialize(project='ee-pythoncolab')  # หรือใส่ชื่อโปรเจกต์ EE ของคุณ

# === คำนวณ GCVI และข้อมูลพื้นที่ ===
@st.cache_data
def compute_gcvi():
    province = ee.FeatureCollection("FAO/GAUL/2015/level1") \
        .filter(ee.Filter.eq('ADM1_NAME', 'Nakhon Sawan'))
    aoi = province.geometry()

    def add_gcvi(img):
        gcvi = img.expression(
            'NIR / GREEN - 1',
            {'NIR': img.select('B8'), 'GREEN': img.select('B3')}
        ).rename('GCVI')
        return img.addBands(gcvi)

    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(aoi) \
        .filterDate('2024-11-01', '2024-12-15') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .map(add_gcvi)

    gcvi = s2.select('GCVI').median().clip(aoi)
    harvested = gcvi.lt(1.0).selfMask()

    pixel_area = ee.Image.pixelArea().updateMask(harvested)
    area_stats = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,
        maxPixels=1e13,
        bestEffort=True
    )
    area_rai = area_stats.getNumber('area').divide(1600)
    tons = area_rai.multiply(0.18)
    trips = tons.divide(4)
    return gcvi, harvested, area_rai.getInfo(), tons.getInfo(), trips.getInfo()

# === Run Computation ===
gcvi_img, harvested_img, rai, tons, trips = compute_gcvi()

# === แสดงค่าผลลัพธ์ ===
col1, col2, col3 = st.columns(3)
col1.metric("พื้นที่เกี่ยวแล้ว (ไร่)", f"{rai:,.0f}")
col2.metric("ปริมาณฟาง (ตัน)", f"{tons:,.0f}")
col3.metric("รถเกี่ยวที่ต้องใช้", f"{trips:,.0f} เที่ยว")

# === แสดงแผนที่ ===
m = geemap.Map(center=[15.7, 100.1], zoom=10)
m.addLayer(gcvi_img, {"min": 0, "max": 2, "palette": ['yellow', 'green', 'darkgreen']}, "GCVI")
m.addLayer(harvested_img, {"palette": ['pink']}, "พื้นที่เกี่ยวแล้ว")
m.to_streamlit(height=600)
