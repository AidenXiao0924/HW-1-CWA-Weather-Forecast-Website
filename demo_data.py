"""Synthetic teaching fixtures, deliberately fixed in time, never presented as live."""
from datetime import date, timedelta
from config import REGIONS, REGION_COORDS

def forecast():
    locations=[]
    for index, region in enumerate(REGIONS):
        elements=[]
        for key, base in [('MinT',22),('MaxT',29)]:
            times=[]
            for day in range(7):
                stamp=(date(2026,9,23)+timedelta(days=day)).isoformat()
                times.append({'startTime':stamp+'T06:00:00+08:00','endTime':stamp+'T18:00:00+08:00','elementValue':[{'value':str(base+index%3+[0,1,2,0,-1,0,1][day])}]})
            elements.append({'elementName':key,'time':times})
        locations.append({'locationName':region,'weatherElement':elements})
    return {'success':'true','records':{'locations':{'location':locations}},'_demo':True}

def observations():
    names=['臺北','臺中','臺南','宜蘭','花蓮','臺東','新竹','嘉義','高雄','恆春','日月潭','阿里山']
    counties=['臺北市','臺中市','臺南市','宜蘭縣','花蓮縣','臺東縣','新竹市','嘉義市','高雄市','屏東縣','南投縣','嘉義縣']
    coords=REGION_COORDS+[(24.81,120.97),(23.48,120.45),(22.63,120.30),(22.00,120.74),(23.86,120.91),(23.51,120.81)]
    temperatures=[28.4,30.1,31.6,26.8,27.3,29.2,28.8,30.5,32.1,29.8,23.2,16.4]
    return {'records':{'Station':[{'StationId':f'DEMO{i+1:03}','StationName':name,'ObsTime':{'DateTime':'2026-09-23T10:00:00+08:00'},'GeoInfo':{'CountyName':counties[i],'TownName':'示範位置','StationAltitude':'20','Coordinates':[{'CoordinateName':'WGS84','StationLatitude':coords[i][0],'StationLongitude':coords[i][1]}]},'WeatherElement':{'AirTemperature':temperatures[i],'RelativeHumidity':65+i,'WindSpeed':round(1+i*.2,1),'WindDirection':90,'AirPressure':1008,'Now':{'Precipitation':0},'Weather':'示範'}} for i,name in enumerate(names)]},'_demo':True}
