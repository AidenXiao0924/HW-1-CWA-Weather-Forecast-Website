"""Pure parsers: CWA nested JSON -> validated daily forecast / observations."""
import csv
import json
import math
import re
from collections import Counter
from datetime import datetime
from config import ROOT, REGIONS, REGION_COUNTIES

def number(value, low=-20, high=50):
    try:
        value = float(value)
        return value if math.isfinite(value) and low <= value <= high else None
    except (ValueError, TypeError):
        return None

def items(value):
    return value if isinstance(value, list) else [value] if isinstance(value, dict) else []

def locations(node):
    if isinstance(node, dict):
        if ('locationName' in node or 'LocationName' in node) and ('weatherElement' in node or 'WeatherElement' in node):
            yield node
        else:
            for value in node.values():
                yield from locations(value)
    elif isinstance(node, list):
        for value in node:
            yield from locations(value)

def element_number(period):
    for candidate in items(period.get('elementValue', period.get('ElementValue', {}))):
        for key in ('value', 'Value', 'MinTemperature', 'MaxTemperature', 'Temperature'):
            if key in candidate:
                return number(candidate[key])
    param = period.get('parameter', {})
    return number(param.get('parameterName'))

def element_value(period):
    return next(iter(items(period.get('elementValue', period.get('ElementValue', {})))), {})

def numeric_text(value, low=-20, high=1000):
    """Read the first finite number from values such as '>= 11'."""
    match = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    return number(match.group(0), low, high) if match else None

def most_common(values):
    values = [str(value).strip() for value in values if str(value or '').strip()]
    return Counter(values).most_common(1)[0][0] if values else None

def parse_forecast(payload):
    daily = {}
    county_dates = {}
    is_county = False
    county_region = {county: region for region, counties in REGION_COUNTIES.items() for county in counties}
    for location in locations(payload.get('records', payload)):
        region = location.get('locationName', location.get('LocationName'))
        county = region if region in county_region else None
        if county:
            is_county = True
            region = county_region[county]
        if region not in REGIONS:
            continue
        for element in items(location.get('weatherElement', location.get('WeatherElement'))):
            name = element.get('elementName', element.get('ElementName'))
            for period in items(element.get('time', element.get('Time'))):
                stamp = period.get('startTime', period.get('StartTime', period.get('dataTime', period.get('DataTime', ''))))
                try:
                    date = datetime.fromisoformat(stamp.replace('Z','+00:00')).date().isoformat()
                except (ValueError, TypeError, AttributeError):
                    continue
                if county:
                    county_dates.setdefault(date, set()).add(datetime.fromisoformat(stamp).hour)
                row = daily.setdefault((region,date), {'regionName':region,'dataDate':date})
                value_node = element_value(period)
                numeric = {
                    'MinT': ('mint', 'min', element_number(period)),
                    '最低溫度': ('mint', 'min', numeric_text(value_node.get('MinTemperature'), -20, 50)),
                    'MaxT': ('maxt', 'max', element_number(period)),
                    '最高溫度': ('maxt', 'max', numeric_text(value_node.get('MaxTemperature'), -20, 50)),
                    '平均溫度': ('temperature_c', 'avg', numeric_text(value_node.get('Temperature'), -20, 50)),
                    '平均相對濕度': ('humidity_percent', 'avg', numeric_text(value_node.get('RelativeHumidity'), 0, 100)),
                    '最低體感溫度': ('min_apparent_c', 'min', numeric_text(value_node.get('MinApparentTemperature'), -30, 60)),
                    '最高體感溫度': ('max_apparent_c', 'max', numeric_text(value_node.get('MaxApparentTemperature'), -30, 60)),
                    '12小時降雨機率': ('precipitation_probability', 'max', numeric_text(value_node.get('ProbabilityOfPrecipitation'), 0, 100)),
                    '紫外線指數': ('uv_index', 'max', numeric_text(value_node.get('UVIndex'), 0, 20)),
                    '風速': ('wind_speed_mps', 'max', numeric_text(value_node.get('WindSpeed'), 0, 150)),
                }.get(name)
                if numeric and numeric[2] is not None:
                    column, operation, value = numeric
                    if operation == 'avg':
                        row.setdefault('_averages', {}).setdefault(column, []).append(value)
                    else:
                        old = row.get(column, value)
                        row[column] = min(old, value) if operation == 'min' else max(old, value)
                categorical = {
                    '天氣現象': ('weather', value_node.get('Weather')),
                    '風向': ('wind_direction', value_node.get('WindDirection')),
                    '最大舒適度指數': ('comfort', value_node.get('MaxComfortIndexDescription')),
                    '最小舒適度指數': ('comfort', value_node.get('MinComfortIndexDescription')),
                    '天氣預報綜合描述': ('description', value_node.get('WeatherDescription')),
                }.get(name)
                if categorical and categorical[1]:
                    row.setdefault('_categories', {}).setdefault(categorical[0], []).append(categorical[1])
                if name == '天氣現象' and value_node.get('WeatherCode'):
                    row.setdefault('_categories', {}).setdefault('weather_code', []).append(value_node['WeatherCode'])
    valid_dates = sorted(d for d,hours in county_dates.items() if min(hours)<=6 and max(hours)>=18)[:7] if is_county else None
    result = []
    for row in daily.values():
        if (valid_dates is not None and row['dataDate'] not in valid_dates) or 'mint' not in row or 'maxt' not in row or row['mint'] > row['maxt']:
            continue
        for column, values in row.pop('_averages', {}).items():
            row[column] = round(sum(values) / len(values), 1)
        for column, values in row.pop('_categories', {}).items():
            row[column] = most_common(values)
        result.append(row)
    return sorted(result, key=lambda r:(r['regionName'],r['dataDate']))

def parse_warnings(payload):
    """Flatten CWA W-C0033-001 county hazards into display-safe records."""
    result = []
    records = payload.get('records', payload)
    for location in items(records.get('location', records.get('Location', []))):
        county = location.get('locationName', location.get('LocationName'))
        conditions = location.get('hazardConditions', location.get('HazardConditions', {}))
        hazards = conditions.get('hazards', conditions.get('Hazards', [])) if isinstance(conditions, dict) else []
        for hazard in items(hazards):
            info = hazard.get('info', hazard.get('Info', {}))
            valid = hazard.get('validTime', hazard.get('ValidTime', {}))
            phenomenon = info.get('phenomena', info.get('Phenomena'))
            if not county or not phenomenon:
                continue
            result.append({
                'county': str(county),
                'phenomenon': str(phenomenon),
                'significance': str(info.get('significance', info.get('Significance', ''))),
                'start_time': valid.get('startTime', valid.get('StartTime')),
                'end_time': valid.get('endTime', valid.get('EndTime')),
            })
    unique = {(r['county'], r['phenomenon'], r['start_time'], r['end_time']): r for r in result}
    return sorted(unique.values(), key=lambda r: (r['county'], r['phenomenon']))

def parse_observations(payload):
    result = {}
    for station in items(payload.get('records', {}).get('Station', [])):
        geo, weather = station.get('GeoInfo', {}), station.get('WeatherElement', {})
        coords = next((c for c in items(geo.get('Coordinates')) if c.get('CoordinateName') == 'WGS84'), {})
        lat, lon = number(coords.get('StationLatitude'),-90,90), number(coords.get('StationLongitude'),-180,180)
        temp, sid = number(weather.get('AirTemperature')), station.get('StationId')
        try:
            observed = datetime.fromisoformat(station['ObsTime']['DateTime'].replace('Z','+00:00'))
            if observed.tzinfo is None:
                from datetime import timezone, timedelta
                observed = observed.replace(tzinfo=timezone(timedelta(hours=8)))
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if lat is None or lon is None or temp is None or not sid:
            continue
        row = dict(station_id=str(sid),station_name=str(station.get('StationName',sid)),county=geo.get('CountyName'),town=geo.get('TownName'),lat=lat,lon=lon,altitude_m=number(geo.get('StationAltitude'),-500,5000),observed_at=observed.isoformat(),temperature_c=temp,
                   humidity_percent=number(weather.get('RelativeHumidity'),0,100),pressure_hpa=number(weather.get('AirPressure'),300,1100),wind_speed_mps=number(weather.get('WindSpeed'),0,150),wind_direction_deg=number(weather.get('WindDirection'),0,360),precipitation_mm=number(weather.get('Now',{}).get('Precipitation'),0,3000),weather=weather.get('Weather'))
        if sid not in result or row['observed_at'] > result[sid]['observed_at']:
            result[sid] = row
    return list(result.values())

if __name__ == '__main__':
    rows = parse_forecast(json.loads((ROOT / 'weather_data.json').read_text(encoding='utf-8')))
    if not rows:
        raise SystemExit('No valid six-region forecast found. Check the raw JSON schema.')
    with (ROOT / 'weather_data.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f,fieldnames=['regionName','dataDate','mint','maxt'])
        writer.writeheader(); writer.writerows(rows)
    print(f'Parsed {len(rows)} daily records into weather_data.csv')
