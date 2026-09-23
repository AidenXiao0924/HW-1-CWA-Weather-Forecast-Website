"""Pure parsers: CWA nested JSON -> validated daily forecast / observations."""
import csv
import json
import math
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
            column = {'MinT':'mint','最低溫度':'mint','MaxT':'maxt','最高溫度':'maxt'}.get(name)
            if not column:
                continue
            for period in items(element.get('time', element.get('Time'))):
                stamp = period.get('startTime', period.get('StartTime', period.get('dataTime', period.get('DataTime', ''))))
                try:
                    date = datetime.fromisoformat(stamp.replace('Z','+00:00')).date().isoformat()
                except (ValueError, TypeError, AttributeError):
                    continue
                if county:
                    county_dates.setdefault(date, set()).add(datetime.fromisoformat(stamp).hour)
                value = element_number(period)
                if value is None:
                    continue
                row = daily.setdefault((region,date), {'regionName':region,'dataDate':date})
                old = row.get(column, value)
                row[column] = min(old,value) if column == 'mint' else max(old,value)
    valid_dates = sorted(d for d,hours in county_dates.items() if min(hours)<=6 and max(hours)>=18)[:7] if is_county else None
    return sorted([r for r in daily.values() if (valid_dates is None or r['dataDate'] in valid_dates) and 'mint' in r and 'maxt' in r and r['mint'] <= r['maxt']], key=lambda r:(r['regionName'],r['dataDate']))

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
