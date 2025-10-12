import folium
from folium import FeatureGroup
from folium.plugins import MarkerCluster, MiniMap, TimestampedGeoJson
from branca.colormap import linear
from branca.element import Element
from shapely.geometry import Point
import geopandas as gpd
import matplotlib
import matplotlib.colors as mcolors
import pandas as pd
import glob, os

# 根据shapefile构筑地图，地图中心定位在国家的几何中心
# “ .dbf”，“。prj”，“。shp”和“ .shx”都是同一ShapeFile的一部分
# 将.shp读入geopandas，它也会自动读取其余部分,得到正确的GeoDataFrame
def create_map_by_country(m, shp_path, border_name = "country border"):
    gdf = gpd.read_file(shp_path)
    # 转换坐标参考系统，保证坐标一致before叠加数据
    #gdf = gdf.to_crs(epsg=4326)
    
    # 计算X国的几何中心
    #center = gdf.geometry.union_all().centroid
    #center_lat, center_lon = center.y, center.x 
    #m = folium.Map(location = [center_lat, center_lon], zoom_start=zoom_start)
    
    # 添加X国边界
    folium.GeoJson(gdf, name=border_name).add_to(m)
    return m

    # 如果要循环添加多个国家边界，main函数里调用belike:
    #for shp, name in [("fi.shp", "Finland"), ("china.shp", "China")]:
    #    m = add_country_border(m, shp, name=name)


# 获取监测站位置并去重
# 数据from AirQualityStation.csv
# 默认保留Air Quality Station Name, Longitude, Latitude 
def get_station_location(path, keep_rows = ["Air Quality Station Name", "Longitude", "Latitude"], only_Finland = False):
    df = pd.read_csv(path)
    # 测试用：筛选出指定国家的监测站
    if only_Finland:
        df = df[df["Country"]=="Finland"]
    
    station_df = df[keep_rows].drop_duplicates(subset="Air Quality Station Name")
    return station_df

# TODO: 如果station_df只用一次，就合并get_station_location和convert函数
# station_info: 监测站信息列名
def convert_df_to_gdf(df, station_info="Air Quality Station Name", lon="Longitude", lat="Latitude"):
    gdf = gpd.GeoDataFrame(
        df[[station_info]],
        geometry=[Point(xy) for xy in zip(df[lon], df[lat])],
        #crs="EPSG:4326"
    )
    return gdf


# 把监测站位置添加到地图上by点聚类函数
# 参数lon和lat：经纬度的列名
def add_points_to_map(m, gdf, lon="Longitude", lat="Latitude"):
    # MarkerCluster()是folium的插件
    # 将多个标记点聚合表示
    marker_cluster = MarkerCluster().add_to(m)
    
    # add stations to the map
    for geo in gdf.geometry:
        # TODO: label定义不完整，要不要显示污染物数据？
        # 得看显示效果
        label ="station name: lon:{}, lat:{}\n".format(geo.x, geo.y)
        folium.Marker(
            location = [geo.y, geo.x],   # location = [纬度，经度]
            icon = folium.Icon(color='blue', icon='cloud'),     # icon样式
            popup=label,    # 点击时显示的信息框
        ).add_to(marker_cluster)
        
    # 添加聚类结果到地图中
    m.add_child(marker_cluster)
    
    # add MiniMap
    minimap = MiniMap(toggle_display=True)
    m.add_child(minimap)
    
    return m


def add_prediction_to_station(station_name, lon, lat, predicted_values, pollutant="Predicted_PM2.5"):
    """添加1个检测站的1种污染物预测时序数据

    Args:
        layer (_type_): 图层
        station_name (_type_): 监测站名称
        lon (_type_): 经纬度
        lat (): 经纬度
        predicted_values (_type_): DataFrame，预测数据
        pollutant (str, optional): 要匹配的污染物. Defaults to "Predicted_PM2.5".

    Returns:
        _type_: 返回一个TimestampedGeoJson
    """

    '''
    定义colormaps, 根据污染物的数值范围直接显示健康等级颜色
    [Good,  Fair,   Moderate,   Poor,   Very Poor,  Extremely Poor]
    [min,   green,  yellow,     red,    purple,     max]
    '''
    BOUNDARY_COLORS = ["green", "green", "yellow", "red", "purple", "purple"]
    cmap_boundaries = {
        "PM2.5": [5, 11, 33, 71, 116,  140],
        "PM10": [15, 31, 83, 158, 233, 270],
        "O3": [60, 81, 111, 141, 171, 180],
        "NOy": [10, 18, 43, 81, 126, 150],
        "SO2": [20, 31, 83, 158, 233, 275],
        "CO": [0, 0, 5, 7, 10, 10],
        "Pb": [0, 0, 0.25, 0.35, 0.5],
        "C6H6": [0, 0, 2, 3.5, 5, 5]
    } 
    
    # 选一个合适的颜色映射，比如从绿色到红色
    cmap_greenred = matplotlib.colormaps['RdYlGn_r']
    def covert_value_to_color(value, vmin, vmax):
        if vmax == vmin: 
            # 防止除0错误
            norm_value = 0.5
        else:
            norm_value = (value - vmin) / (vmax - vmin)
        color = cmap_greenred(norm_value)
        return mcolors.rgb2hex(color)
        
    # 监测站的相关数据
    points = [
        {"time": str(row["Date"]),
        "coordinates": [lon, lat],
        "color": covert_value_to_color(
            row[pollutant],
            predicted_values[pollutant].min(),
            predicted_values[pollutant].max()
        ),      # 这里再转换颜色
        "value": row[pollutant],
        "Air quality station name": station_name
        }
        for _, row in predicted_values.iterrows()
    ]

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": point["coordinates"],
            },
            "properties": {
                "time": point["time"],
                "tooltip": f'{point["Air quality station name"]}: {point["value"]}',
                "icon": "circle",
                "iconstyle": {
                    "fillColor": point["color"],
                    "fillOpacity": 0.6,
                    "stroke": False,
                    # TODO:小优化（optional）根据不同污染程度，设置不同半径
                    "radius": 40   # 测试时调大点，因为就测一个点
                },
            },
        }
        for point in points
    ]

    tsgj = folium.plugins.TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period="PT1H",
        auto_play=False,
        loop=False,
        max_speed=100,
        loop_button=True,
        date_options="YYYY/MM/DD HH:MM:SS",
        time_slider_drag_update=True,
        duration="P2M",
    #).add_to(m)
    )
    return tsgj
    
# TODO: 显示到n个page
def add_all_pollutants_to_station(m, gdf_stations, all_predictions, pollutant, gdf_col_name="Air Quality Station Name"):        
    """把n个监测站的1种预测值都放进1个网页

    Args:
        m (_type_): 地图，folium
        gdf_stations (_type_): gdf数据，列名依次是 Air Quality Station Name和geometry
        all_predictions (_type_): 整合了所有csv的预测时序数据，覆盖所有监测站和污染物
        （已删除）pollutants (_type_): 污染物列表
        gdf_col_name (str, optional): 好像是gdf的监测站列名，遗老属于是. Defaults to "Air quality station name".

    Returns:
        map: _description_
    """
    # 遍历监测站，每个站点的数据单独绘制
    for station_name in gdf_stations[gdf_col_name].unique():
        print("开始绘制监测站：", station_name)
        
        # 拿到监测站名字+位置
        station_info = gdf_stations[gdf_stations[gdf_col_name] == station_name]
        if station_info.empty:
            print(f"找不到监测站{station_name}，请核对名字是否正确")
            continue
        lon, lat = station_info.geometry.iloc[0].x, station_info.geometry.iloc[0].y
    
        # 筛选出该监测站的预测值
        df_station = all_predictions[all_predictions["station_name"] == station_name]
    
    # 绘制单站点时序数据
    #layer_pollutant = add_prediction_to_station(
    tsgj = add_prediction_to_station(
        #m=m,
        station_name=station_name,
        lon=lon,
        lat=lat,
        predicted_values=df_station,
        pollutant=pollutant
    )
    
    tsgj.add_to(m)
    return m

'''
#
def get_air_quality_level(pollutant_value):    
    # 调用例子：color = cma ps["PM2.5"](value)
    cmaps = {
        pollutant: branca.colormap.LinearColormap(
            colors=BOUNDARY_COLORS, 
            index=boundaries,
            vmin=boundaries[0], vmax=boundaries[-1],
            caption=f"{pollutant} ug.m-3",
        )
        for pollutant, boundaries in cmap_boundaries.items()
    }
'''
    
         
# 读取模型输出的预测值
# 列：Date,Predicted_PM2.5,Predicted_PM10,Predicted_SO2,Predicted_O3
def get_predicted_values(prediction_path):
    df = pd.read_csv(prediction_path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# 读取所有csv+合并df
def get_all_predictions(predictions_path):
    files = glob.glob(os.path.join(predictions_path, "predictions_station_*.csv"))
    
    # 初始化为DataFrame的话，循环合并的时候低效
    dfs = []
    for file in files:
        # 提取监测站名字
        filename = os.path.basename(file)
        station_name = filename.replace("predictions_station_", "").replace(".csv", "")
        
        df = pd.read_csv(file)
        # 新建一列，存放station name
        df["station_name"] = station_name
        dfs.append(df)

    # 合并
    all_predictions = pd.concat(dfs, ignore_index=True)
    return all_predictions


if __name__ == "__main__":
    '''
        TODO:
        Popups-可以向地图上的标记添加弹出介绍
        Simple popups-弹出文字信息
        函数类型检查写不写？
    
    '''
    station_file = ".\data\Air pollution data\metadata\AirQualityStation.csv"
    
    prediction_files = ".\data\predictions\predictions_station_Kaleva.csv"
    predictions_path = r".\data\predictions"
    
    station_name = "Kaleva"     # TODO：暂且先写死
    shp_path = r"data\GIS data\borders\fi.shp"
    HELSINKI_GPS = (60.1699, 24.9384)
    
    # 读取监测站位置和预测值(测试先只考虑画芬兰监测站)
    station_df = get_station_location(station_file, only_Finland=True)
    #predicted_values = get_predicted_values(prediction_files)
    all_predictions = get_all_predictions(predictions_path)
    
    # 构造GeoDataFrame
    gdf = convert_df_to_gdf(station_df)

    # 获取所有污染物列名
    pollutants = [col for col in all_predictions.columns if col.startswith("Predicted_")]
    if not pollutants:
        print("没找到任何污染物列!")

    for pollutant in pollutants:
        # 以芬兰为核心创建地图
        m = folium.Map(location=HELSINKI_GPS, zoom_start=5)
        m = create_map_by_country(m, shp_path)
        
        # 并在图上画出监测站
        m = add_points_to_map(m, gdf)    
        
        print(f"=== 开始绘制污染物：{pollutant} ===")

        # 添加预测值
        #m = add_prediction_to_stations(m, station_name, gdf, all_predictions)
        m = add_all_pollutants_to_station(
            m=m,
            gdf_stations=gdf,
            all_predictions=all_predictions,
            pollutant=pollutant
        )

        m
        m.save(f"{pollutant}.html")
