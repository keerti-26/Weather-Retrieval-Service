Create table if not exists weather_forecast(
    id TEXT Primary Key,
    location TEXT,
    number_counter INTEGER, 
    day TEXT,
    starttime TIMESTAMP,
    endtime TIMESTAMP,
    temperature INTEGER,
    precipitation_prob INTEGER,
    wind_speed TEXT,
    wind_direction TEXT,
    detailed_forecast TEXT
);

CREATE INDEX ON weather_forecast(location);